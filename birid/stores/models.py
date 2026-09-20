from django.core.validators import RegexValidator
from django.db import models

from core.models import AbstractAuthAccount, TimestampedModel

HEX_COLOR_VALIDATOR = RegexValidator(
    regex=r"^#(?:[0-9a-fA-F]{3}){1,2}$",
    message="Enter a valid HEX color, e.g. #FF0000 or #F00.",
)


class Store(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")

    phone = models.CharField(max_length=32, blank=True, default="")
    email = models.EmailField(blank=True, default="")

    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class StoreAdmin(AbstractAuthAccount):
    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="admins")

    def __str__(self) -> str:
        return f"{self.login} ({self.store.name})"


class Icon(models.Model):
    """Global icon catalog - the frontend lists this so a store admin can pick one per service."""

    ALLOWED_FILTERS = {"name"}

    name = models.CharField(max_length=100, unique=True)

    def __str__(self) -> str:
        return self.name


class SocialPlatform(models.TextChoices):
    INSTAGRAM = "instagram", "Instagram"
    TELEGRAM = "telegram", "Telegram"
    WHATSAPP = "whatsapp", "WhatsApp"
    VK = "vk", "VK"
    TIKTOK = "tiktok", "TikTok"
    YOUTUBE = "youtube", "YouTube"
    FACEBOOK = "facebook", "Facebook"
    OTHER = "other", "Other"


class StoreSocialLink(TimestampedModel):
    ALLOWED_FILTERS = {"platform", "nickname", "visible", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="social_links")
    platform = models.CharField(max_length=20, choices=SocialPlatform.choices)
    nickname = models.CharField(max_length=150, blank=True, default="")
    url = models.URLField()
    visible = models.BooleanField(default=True)

    def __str__(self) -> str:
        return f"{self.platform}:{self.nickname or self.url}"


class StoreAddress(TimestampedModel):
    ALLOWED_FILTERS = {"name", "address", "landmark", "working_hours", "phone", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="addresses")
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=500)
    landmark = models.CharField(max_length=255, blank=True, default="")
    working_hours = models.CharField(max_length=255, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")

    def __str__(self) -> str:
        return self.name


class StoreContact(TimestampedModel):
    ALLOWED_FILTERS = {"name", "role", "phone", "telegram", "has_telegram", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="contacts")
    name = models.CharField(max_length=150)
    role = models.CharField(max_length=150, blank=True, default="")
    phone = models.CharField(max_length=32, blank=True, default="")
    hours = models.CharField(max_length=255, blank=True, default="")
    telegram = models.CharField(max_length=150, blank=True, default="")
    has_telegram = models.BooleanField(default=False)

    def __str__(self) -> str:
        return self.name


class StoreService(TimestampedModel):
    ALLOWED_FILTERS = {"title", "icon", "kicker", "visible", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="services")
    icon = models.ForeignKey(Icon, on_delete=models.PROTECT, related_name="services")
    title = models.CharField(max_length=255)
    kicker = models.CharField(max_length=255, blank=True, default="")
    description = models.TextField(blank=True, default="")
    visible = models.BooleanField(default=True)

    def __str__(self) -> str:
        return self.title


class StoreColor(TimestampedModel):
    ALLOWED_FILTERS = {"name", "hex_code", "created_at"}

    store = models.ForeignKey(Store, on_delete=models.CASCADE, related_name="colors")
    name = models.CharField(max_length=100)
    hex_code = models.CharField(max_length=7, validators=[HEX_COLOR_VALIDATOR])

    def __str__(self) -> str:
        return f"{self.name} ({self.hex_code})"
