import io
from datetime import timedelta

from celery import shared_task
from django.core.files.base import ContentFile
from django.utils import timezone
from PIL import Image


from .models import (
    PhotoProcessingStatus,
    RenditionQuality,
    StoreCategory,
    StoreProductPhoto,
    StoreProductPhotoRendition,
)

# Renditions are always encoded as WebP regardless of the original's format
# (JPEG/PNG/HEIC/...) - smaller files, near-universal browser support, and
# since we're already decoding+resizing the original for these anyway,
# targeting WebP instead of matching-the-source-format costs nothing extra.
_TARGET_HEIGHTS = {
    RenditionQuality.LARGE: 1080,
    RenditionQuality.MEDIUM: 720,
    RenditionQuality.SMALL: 320,
}
_RENDITION_EXTENSION = ".webp"
_RENDITION_CONTENT_TYPE = "image/webp"
_RENDITION_QUALITY = 80

_COVER_SIZE = 1000

# How stale (no status update) a non-ready photo must be before the periodic
# sweep re-queues it. Must comfortably outlast the retry backoff above
# (15+30+60+120+240s ~= 7.5min worst case) so the sweep never fires on a photo
# Celery is still actively retrying on its own.
_STUCK_THRESHOLD = timedelta(minutes=15)


@shared_task(bind=True, max_retries=5)
def generate_photo_renditions(self, photo_id: int) -> None:
    try:
        photo = StoreProductPhoto.objects.get(id=photo_id)
    except StoreProductPhoto.DoesNotExist:
        return

    try:
        with photo.image.open("rb") as source:
            original_bytes = source.read()

        with Image.open(io.BytesIO(original_bytes)) as original_image:
            original_image.load()
            source_image = _to_webp_compatible_mode(original_image)

            # Retry-safe: clear any renditions a previous failed attempt left
            # half-created, otherwise re-creating them collides with the
            # (photo, quality) unique constraint and fails immediately again.
            photo.renditions.all().delete()

            for quality, target_height in _TARGET_HEIGHTS.items():
                resized = _resize_to_height(source_image, target_height)
                buffer = io.BytesIO()
                resized.save(buffer, format="WEBP", quality=_RENDITION_QUALITY)

                rendition = StoreProductPhotoRendition.objects.create(
                    store_id=photo.store_id, photo=photo, quality=quality,
                )
                content_file = ContentFile(buffer.getvalue())
                content_file.content_type = _RENDITION_CONTENT_TYPE
                rendition.image.save(f"{quality}{_RENDITION_EXTENSION}", content_file, save=True)

        photo.processing_status = PhotoProcessingStatus.READY
        photo.save(update_fields=["processing_status", "updated_at"])
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            photo.processing_status = PhotoProcessingStatus.FAILED
            photo.save(update_fields=["processing_status", "updated_at"])
            raise
        # Exponential backoff (15s, 30s, 60s, 120s, 240s), capped at 5 minutes.
        raise self.retry(exc=exc, countdown=min(15 * 2 ** self.request.retries, 300))


@shared_task(bind=True, max_retries=5)
def process_category_cover(self, category_id: int) -> None:
    try:
        category = StoreCategory.objects.get(id=category_id)
    except StoreCategory.DoesNotExist:
        return
    if not category.cover:
        return

    try:
        with category.cover.open("rb") as source:
            original_bytes = source.read()

        with Image.open(io.BytesIO(original_bytes)) as original_image:
            original_image.load()
            source_image = _to_webp_compatible_mode(original_image)
            square = _crop_to_square(source_image, _COVER_SIZE)

            buffer = io.BytesIO()
            square.save(buffer, format="WEBP", quality=_RENDITION_QUALITY)

            content_file = ContentFile(buffer.getvalue())
            content_file.content_type = _RENDITION_CONTENT_TYPE
            category.cover_processed.save(f"cover{_RENDITION_EXTENSION}", content_file, save=False)

        category.cover_processing_status = PhotoProcessingStatus.READY
        category.save(update_fields=["cover_processed", "cover_processing_status", "updated_at"])
    except Exception as exc:
        if self.request.retries >= self.max_retries:
            category.cover_processing_status = PhotoProcessingStatus.FAILED
            category.save(update_fields=["cover_processing_status", "updated_at"])
            raise
        raise self.retry(exc=exc, countdown=min(15 * 2 ** self.request.retries, 300))


@shared_task
def sweep_stuck_photo_processing() -> None:
    """
    Safety net for photos/covers where the processing task never ran to
    completion at all - broker/worker restarted mid-task, .delay() was lost,
    etc. Celery's own per-task retries (above) already handle ordinary
    transient failures; this only re-queues work stale well past that.
    """
    cutoff = timezone.now() - _STUCK_THRESHOLD

    stuck_photo_ids = StoreProductPhoto.objects.filter(
        processing_status__in=[PhotoProcessingStatus.PENDING, PhotoProcessingStatus.FAILED],
        updated_at__lt=cutoff,
    ).values_list("id", flat=True)
    for photo_id in stuck_photo_ids:
        generate_photo_renditions.delay(photo_id)

    stuck_category_ids = StoreCategory.objects.filter(
        cover_processing_status__in=[PhotoProcessingStatus.PENDING, PhotoProcessingStatus.FAILED],
        updated_at__lt=cutoff,
    ).values_list("id", flat=True)
    for category_id in stuck_category_ids:
        process_category_cover.delay(category_id)


def _to_webp_compatible_mode(image: Image.Image) -> Image.Image:
    """Palette/CMYK/grayscale sources need converting before Pillow can encode them as WebP."""
    if image.mode in ("RGB", "RGBA"):
        return image
    if image.mode == "P":
        return image.convert("RGBA" if "transparency" in image.info else "RGB")
    return image.convert("RGB")


def _resize_to_height(image: Image.Image, target_height: int) -> Image.Image:
    """Downscale only (never upscale a smaller original), preserving aspect ratio."""
    if image.height <= target_height:
        return image.copy()
    ratio = target_height / image.height
    target_width = max(1, round(image.width * ratio))
    return image.resize((target_width, target_height), Image.LANCZOS)


def _crop_to_square(image: Image.Image, target_size: int) -> Image.Image:
    """
    Center-crop to 1:1, then resize to exactly target_size x target_size.
    Unlike _resize_to_height, this upscales a smaller source too - a category
    cover must always come out exactly target_size for a consistent grid,
    there's no "preserve the smaller original" case here.
    """
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    cropped = image.crop((left, top, left + side, top + side))
    if side == target_size:
        return cropped
    return cropped.resize((target_size, target_size), Image.LANCZOS)
