from django.contrib.auth.hashers import check_password, make_password
from django.db import models


class AbstractAuthAccount(models.Model):
    """
    Shared base for every principal that authenticates via JWT (store admins,
    buyers, ...). Not Django's AbstractBaseUser on purpose - auth here is
    stateless (JWT, no sessions), and different principal types are issued
    tokens signed with different RSA keypairs, so there is no single
    AUTH_USER_MODEL that could represent all of them.
    """

    login = models.CharField(max_length=255, unique=True)
    hashed_password = models.CharField(max_length=255)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True

    def set_password(self, raw_password: str) -> None:
        self.hashed_password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password(raw_password, self.hashed_password)

    @property
    def is_authenticated(self) -> bool:
        return True


class TimestampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        # Default list ordering for every subclass. A subclass that declares
        # its own Meta must inherit this one (`class Meta(TimestampedModel.Meta)`)
        # to keep it - Django does not merge an unrelated child Meta with the
        # abstract parent's automatically.
        ordering = ["-created_at"]
