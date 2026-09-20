from django.db import models

from core.models import TimestampedModel
from products.models import StoreProduct
from stores.models import Store


class NewsType(models.TextChoices):
    EVENT = "event", "Event"
    DISCOUNT = "discount", "Discount"
    HOLIDAY = "holiday", "Holiday"
    OTHER = "other", "Other"


class NewsStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    ACTIVE = "active", "Active"
    ARCHIVED = "archived", "Archived"


class StoreNews(TimestampedModel):
    ALLOWED_FILTERS = {"title", "news_type", "status", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="news")

    title = models.CharField(max_length=255)
    news_type = models.CharField(max_length=20, choices=NewsType.choices)
    slug = models.SlugField(max_length=255)
    description = models.TextField(blank=True, default="")  # may contain HTML

    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()

    status = models.CharField(max_length=20, choices=NewsStatus.choices, default=NewsStatus.DRAFT)

    products = models.ManyToManyField(StoreProduct, related_name="news_items", blank=True)

    class Meta(TimestampedModel.Meta):
        verbose_name_plural = "store news"
        constraints = [
            models.UniqueConstraint(fields=["store", "slug"], name="uniq_news_slug_per_store"),
        ]

    def __str__(self) -> str:
        return self.title
