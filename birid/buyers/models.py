import uuid as uuid_lib
from pathlib import Path

from django.db import models

from core.models import AbstractAuthAccount


class BuyerAvatarProcessingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


def buyer_avatar_upload_path(instance: "Buyer", filename: str) -> str:
    suffix = Path(filename).suffix
    return f"{uuid_lib.uuid4()}{suffix}"


def buyer_avatar_processed_upload_path(instance: "Buyer", filename: str) -> str:
    suffix = Path(filename).suffix
    return f"{uuid_lib.uuid4()}{suffix}"


class Buyer(AbstractAuthAccount):
    class Gender(models.TextChoices):
        MALE = "male", "Male"
        FEMALE = "female", "Female"

    last_name = models.CharField(max_length=150)
    first_name = models.CharField(max_length=150)
    middle_name = models.CharField(max_length=150, blank=True, default="")

    age = models.PositiveSmallIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=Gender.choices, null=True, blank=True)
    city = models.CharField(max_length=150, blank=True, default="")

    # Uploaded as-is; a worker center-crops it to 1:1 and resizes it into
    # avatar_photo_processed (see buyers/tasks.py) - same pattern as
    # StoreCategory.cover/cover_processed in the products app.
    avatar_photo = models.ImageField(upload_to=buyer_avatar_upload_path, null=True, blank=True)
    avatar_photo_processed = models.ImageField(
        upload_to=buyer_avatar_processed_upload_path, null=True, blank=True, editable=False,
    )
    avatar_processing_status = models.CharField(
        max_length=20, choices=BuyerAvatarProcessingStatus.choices, null=True, blank=True, default=None,
    )

    favorite_products = models.ManyToManyField(
        "products.StoreProduct", related_name="favorited_by_buyers", blank=True,
    )
    favorite_stores = models.ManyToManyField(
        "stores.Store", related_name="favorited_by_buyers", blank=True,
    )

    class Meta:
        # sweep_stuck_avatar_processing (buyers/tasks.py) filters on exactly this pair
        indexes = [models.Index(fields=["avatar_processing_status", "updated_at"])]

    def __str__(self) -> str:
        return f"{self.last_name} {self.first_name}".strip()
