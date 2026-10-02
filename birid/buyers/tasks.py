import io
from datetime import timedelta

from celery import shared_task
from django.core.files.base import ContentFile
from django.db.models import F
from django.utils import timezone
from PIL import Image

from .models import Buyer, BuyerAvatarProcessingStatus

_AVATAR_SIZE = 500
_AVATAR_EXTENSION = ".webp"
_AVATAR_CONTENT_TYPE = "image/webp"
_AVATAR_QUALITY = 80

# Must comfortably outlast the retry backoff below (15+30+60+120+240s ~= 7.5min
# worst case) so the sweep never fires on an avatar Celery is still retrying on its own.
_STUCK_THRESHOLD = timedelta(minutes=15)

# The sweep gives up on an avatar after this many re-queues - it stays `failed` from then on.
_MAX_SWEEP_RETRIES = 5


@shared_task(bind=True, max_retries=5)
def process_buyer_avatar(self, buyer_id: int) -> None:
    try:
        buyer = Buyer.objects.get(id=buyer_id)
    except Buyer.DoesNotExist:
        return
    if not buyer.avatar_photo:
        return

    try:
        with buyer.avatar_photo.open("rb") as source:
            original_bytes = source.read()

        with Image.open(io.BytesIO(original_bytes)) as original_image:
            original_image.load()
            source_image = _to_webp_compatible_mode(original_image)
            square = _crop_to_square(source_image, _AVATAR_SIZE)

            buffer = io.BytesIO()
            square.save(buffer, format="WEBP", quality=_AVATAR_QUALITY)

            content_file = ContentFile(buffer.getvalue())
            content_file.content_type = _AVATAR_CONTENT_TYPE
            buyer.avatar_photo_processed.save(f"avatar{_AVATAR_EXTENSION}", content_file, save=False)

        buyer.avatar_processing_status = BuyerAvatarProcessingStatus.READY
        buyer.save(update_fields=["avatar_photo_processed", "avatar_processing_status", "updated_at"])
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            buyer.avatar_processing_status = BuyerAvatarProcessingStatus.FAILED
            buyer.save(update_fields=["avatar_processing_status", "updated_at"])
            raise
        # Exponential backoff (15s, 30s, 60s, 120s, 240s), capped at 5 minutes.
        raise self.retry(exc=exc, countdown=min(15 * 2 ** self.request.retries, 300))


@shared_task
def sweep_stuck_avatar_processing() -> None:
    """
    Safety net for avatars where the processing task never ran to completion
    at all - broker/worker restarted mid-task, .delay() was lost, etc.
    Celery's own per-task retries (above) already handle ordinary transient
    failures; this only re-queues work stale well past that.
    """
    now = timezone.now()
    cutoff = now - _STUCK_THRESHOLD

    stuck_buyer_ids = list(Buyer.objects.filter(
        avatar_processing_status__in=[BuyerAvatarProcessingStatus.PENDING, BuyerAvatarProcessingStatus.FAILED],
        updated_at__lt=cutoff,
        avatar_processing_retries__lt=_MAX_SWEEP_RETRIES,
    ).values_list("id", flat=True))
    # Bumping updated_at keeps the next sweep from re-queuing an avatar whose task is still queued.
    Buyer.objects.filter(id__in=stuck_buyer_ids).update(
        avatar_processing_retries=F("avatar_processing_retries") + 1, updated_at=now,
    )
    for buyer_id in stuck_buyer_ids:
        process_buyer_avatar.delay(buyer_id)


def _to_webp_compatible_mode(image: Image.Image) -> Image.Image:
    """Palette/CMYK/grayscale sources need converting before Pillow can encode them as WebP."""
    if image.mode in ("RGB", "RGBA"):
        return image
    if image.mode == "P":
        return image.convert("RGBA" if "transparency" in image.info else "RGB")
    return image.convert("RGB")


def _crop_to_square(image: Image.Image, target_size: int) -> Image.Image:
    """
    Center-crop to 1:1, then resize to exactly target_size x target_size.
    Upscales a smaller source too - an avatar must always come out exactly
    target_size, there's no "preserve the smaller original" case here.
    """
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    cropped = image.crop((left, top, left + side, top + side))
    if side == target_size:
        return cropped
    return cropped.resize((target_size, target_size), Image.LANCZOS)
