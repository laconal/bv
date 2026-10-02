from .models import StoreProductPhoto
from .tasks import generate_photo_renditions


def replace_image(owner, image_file) -> None:
    """
    Points `owner.image` (StoreNews/StoreDiscount) at a new StoreProductPhoto
    built from `image_file` - or clears it when `image_file` is None - then
    deletes the previous photo with its files, unless something else (a
    product variant, another news/discount) still uses it.
    """
    previous = owner.image
    if image_file is None:
        owner.image = None
    else:
        photo = StoreProductPhoto.objects.create(store=owner.store, image=image_file)
        generate_photo_renditions.delay(photo.id)
        owner.image = photo
    owner.save(update_fields=["image", "updated_at"])
    delete_photo_if_unused(previous)


def delete_with_image(owner) -> None:
    """Deletes a StoreNews/StoreDiscount together with its photo (unless something else still uses that photo)."""
    image = owner.image
    owner.delete()
    delete_photo_if_unused(image)


def delete_photo_if_unused(photo) -> None:
    if photo is not None and not photo.is_referenced():
        photo.delete_with_files()
