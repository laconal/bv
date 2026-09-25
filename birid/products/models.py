import uuid as uuid_lib
from pathlib import Path

from django.db import models

from core.models import TimestampedModel
from stores.models import Store, StoreColor


class PhotoProcessingStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    READY = "ready", "Ready"
    FAILED = "failed", "Failed"


def product_photo_upload_path(instance: "StoreProductPhoto", filename: str) -> str:
    """
    Storage key is the photo's own uuid (no extension) - MinIO serves it fine
    off its stored Content-Type. Capturing `filename` here (Django calls this
    before assigning `instance.image`) is also how `original_filename` gets set,
    without a separate upload step or S3 round-trip to read it back.
    """
    instance.original_filename = filename
    return str(instance.uuid)


def category_cover_upload_path(instance: "StoreCategory", filename: str) -> str:
    suffix = Path(filename).suffix
    return f"{uuid_lib.uuid4()}{suffix}"


def category_cover_processed_upload_path(instance: "StoreCategory", filename: str) -> str:
    suffix = Path(filename).suffix
    return f"{uuid_lib.uuid4()}{suffix}"


class StoreCategory(TimestampedModel):
    ALLOWED_FILTERS = {"name", "parent", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="categories")
    name = models.CharField(max_length=255)
    parent = models.ForeignKey(
        "self", on_delete=models.PROTECT, null=True, blank=True, related_name="children",
    )

    # Uploaded as-is; a worker center-crops it to 1:1 and resizes to exactly
    # 1000x1000 into `cover_processed` (see products/tasks.py) - unlike
    # product photo renditions, a cover has one required canonical size, not
    # a preserve-aspect-ratio ladder, so it upscales a smaller source too.
    cover = models.ImageField(upload_to=category_cover_upload_path, null=True, blank=True)
    cover_processed = models.ImageField(
        upload_to=category_cover_processed_upload_path, null=True, blank=True, editable=False,
    )
    cover_processing_status = models.CharField(
        max_length=20, choices=PhotoProcessingStatus.choices, null=True, blank=True, default=None,
    )

    class Meta(TimestampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["store", "name"], name="uniq_category_name_per_store"),
        ]
        # sweep_stuck_photo_processing (products/tasks.py) filters on exactly this pair
        indexes = [models.Index(fields=["cover_processing_status", "updated_at"])]

    def __str__(self) -> str:
        return self.name


class StoreTag(TimestampedModel):
    ALLOWED_FILTERS = {"name", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="tags")
    name = models.CharField(max_length=255)

    class Meta(TimestampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["store", "name"], name="uniq_tag_name_per_store"),
        ]

    def __str__(self) -> str:
        return self.name


class StoreProductMaterialCategory(TimestampedModel):
    """Grouping for materials only - unrelated to StoreCategory (which groups products)."""

    ALLOWED_FILTERS = {"name", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="product_material_categories")
    name = models.CharField(max_length=255)

    class Meta(TimestampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["store", "name"], name="uniq_product_material_category_name_per_store"),
        ]

    def __str__(self) -> str:
        return self.name


class StoreProductMaterial(TimestampedModel):
    ALLOWED_FILTERS = {"name", "category", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="product_materials")
    name = models.CharField(max_length=255)
    category = models.ForeignKey(
        StoreProductMaterialCategory, on_delete=models.SET_NULL, null=True, blank=True, related_name="materials",
    )

    class Meta(TimestampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["store", "name"], name="uniq_product_material_name_per_store"),
        ]

    def __str__(self) -> str:
        return self.name


class StoreProduct(TimestampedModel):
    ALLOWED_FILTERS = {
        "store", "name", "category", "subcategory", "brand", "manufacture", "materials",
        "tags", "color", "size", "price_sale", "price_rental", "price_tailoring",
        "is_sellable", "is_rentable", "blur_image_in_site", "created_at",
    }

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="products")

    name = models.CharField(max_length=255)
    category = models.ForeignKey(
        StoreCategory, on_delete=models.PROTECT, related_name="products_in_category",
    )
    subcategory = models.ForeignKey(
        StoreCategory, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="products_in_subcategory",
    )
    description = models.TextField(blank=True, default="")
    brand = models.CharField(max_length=255, blank=True, default="")
    manufacture = models.CharField(max_length=255, blank=True, default="")
    slug = models.SlugField(max_length=255)

    materials = models.ManyToManyField(StoreProductMaterial, related_name="products", blank=True)
    tags = models.ManyToManyField(StoreTag, related_name="products", blank=True)
    color = models.ForeignKey(
        StoreColor, on_delete=models.SET_NULL, null=True, blank=True, related_name="products",
    )
    size = models.IntegerField(null=True, blank=True)

    price_sale = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)
    price_rental = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)
    price_tailoring = models.DecimalField(max_digits=30, decimal_places=2, null=True, blank=True)

    is_sellable = models.BooleanField(default=True)
    is_rentable = models.BooleanField(default=False)
    blur_image_in_site = models.BooleanField(default=False)

    # Incremented only when GET .../public/products/{id}/ is hit by an
    # authenticated buyer (see products/public_viewsets.py) - anonymous
    # browsing and store-admin access don't count.
    views = models.PositiveIntegerField(default=0, editable=False)

    class Meta(TimestampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["store", "slug"], name="uniq_product_slug_per_store"),
        ]

    def __str__(self) -> str:
        return self.name


class StoreProductView(TimestampedModel):
    """
    One row per authenticated-buyer view of a product (see
    products/public_viewsets.py's retrieve()) - StoreProduct.views is a
    cheap lifetime running total, this is what lets the reports (see
    products/reports.py) count views within an arbitrary date range.
    """

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="product_views")
    product = models.ForeignKey(StoreProduct, on_delete=models.CASCADE, related_name="view_events")

    class Meta(TimestampedModel.Meta):
        indexes = [models.Index(fields=["product", "created_at"])]

    def __str__(self) -> str:
        return f"view of {self.product_id} at {self.created_at}"


class RenditionQuality(models.TextChoices):
    LARGE = "large", "Large (1080p, WebP)"
    MEDIUM = "medium", "Medium (720p, WebP)"
    SMALL = "small", "Small (320p, WebP)"


def photo_rendition_upload_path(instance: "StoreProductPhotoRendition", filename: str) -> str:
    suffix = Path(filename).suffix
    return f"{instance.photo.uuid}_{instance.quality}{suffix}"


class StoreProductPhoto(TimestampedModel):
    ALLOWED_FILTERS = {"original_filename", "processing_status", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="product_photos")
    uuid = models.UUIDField(default=uuid_lib.uuid4, unique=True, editable=False)
    image = models.ImageField(upload_to=product_photo_upload_path)
    original_filename = models.CharField(max_length=255, blank=True, default="")

    # original is available immediately; medium/small renditions are generated
    # asynchronously by a Celery worker (see products/tasks.py) - this tracks that.
    processing_status = models.CharField(
        max_length=20, choices=PhotoProcessingStatus.choices, default=PhotoProcessingStatus.PENDING,
    )

    class Meta(TimestampedModel.Meta):
        # sweep_stuck_photo_processing (products/tasks.py) filters on exactly this pair
        indexes = [models.Index(fields=["processing_status", "updated_at"])]

    def __str__(self) -> str:
        return str(self.uuid)


class StoreProductPhotoRendition(TimestampedModel):
    """A resized copy (medium/small) of a StoreProductPhoto, generated by a background worker."""

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="product_photo_renditions")
    photo = models.ForeignKey(StoreProductPhoto, on_delete=models.CASCADE, related_name="renditions")
    quality = models.CharField(max_length=20, choices=RenditionQuality.choices)
    image = models.ImageField(upload_to=photo_rendition_upload_path)

    class Meta(TimestampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["photo", "quality"], name="uniq_rendition_quality_per_photo"),
        ]

    def __str__(self) -> str:
        return f"{self.photo_id}:{self.quality}"


class StoreProductVariant(TimestampedModel):
    """
    A photo set variant of a product (e.g. different angles/looks). `photos`
    is many-to-many rather than a plain FK on Photo, since the same uploaded
    photo can be reused across more than one variant.
    """

    ALLOWED_FILTERS = {"product", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="product_variants")
    product = models.ForeignKey(StoreProduct, on_delete=models.CASCADE, related_name="variants")
    photos = models.ManyToManyField(StoreProductPhoto, related_name="variants", blank=True)

    def __str__(self) -> str:
        return f"Variant #{self.id} of {self.product_id}"


class DiscountType(models.TextChoices):
    FIXED_AMOUNT = "fixed_amount", "Fixed amount"
    PERCENTAGE = "percentage", "Percentage"


class DiscountStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class StoreDiscount(TimestampedModel):
    ALLOWED_FILTERS = {"title", "starts_at", "ends_at", "status", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="discounts")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    # Both optional - no ends_at means the discount never expires on its own.
    starts_at = models.DateTimeField(null=True, blank=True)
    ends_at = models.DateTimeField(null=True, blank=True)

    status = models.CharField(max_length=20, choices=DiscountStatus.choices, default=DiscountStatus.DRAFT)

    products = models.ManyToManyField(StoreProduct, through="StoreDiscountProduct", related_name="discounts")

    def __str__(self) -> str:
        return self.title


class StoreDiscountProduct(TimestampedModel):
    """
    discount_type/value live here, not on StoreDiscount - a discount attached
    to several products can give one a fixed amount off and another a percent
    off, so those aren't a single flat value per discount.
    """

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="discount_products")
    discount = models.ForeignKey(StoreDiscount, on_delete=models.CASCADE, related_name="discount_products")
    product = models.ForeignKey(StoreProduct, on_delete=models.CASCADE, related_name="product_discounts")

    discount_type = models.CharField(max_length=20, choices=DiscountType.choices)
    value = models.DecimalField(max_digits=30, decimal_places=2)

    class Meta(TimestampedModel.Meta):
        constraints = [
            models.UniqueConstraint(fields=["discount", "product"], name="uniq_product_per_discount"),
        ]

    def __str__(self) -> str:
        return f"{self.discount_id}:{self.product_id}"
