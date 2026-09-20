from django import forms
from django.contrib import admin

from .models import Store, StoreAdmin


class StoreAdminAccountForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, required=False,
        help_text="Leave blank to keep the current password.",
    )

    class Meta:
        model = StoreAdmin
        exclude = ["hashed_password"]

    def save(self, commit=True):
        instance = super().save(commit=False)
        raw_password = self.cleaned_data.get("password")
        if raw_password:
            instance.set_password(raw_password)
        elif not instance.hashed_password:
            raise forms.ValidationError("Password is required for a new account.")
        if commit:
            instance.save()
        return instance


@admin.register(Store)
class StoreModelAdmin(admin.ModelAdmin):
    list_display = ["id", "name", "phone", "email", "active", "created_at"]
    search_fields = ["name", "email", "phone"]


@admin.register(StoreAdmin)
class StoreAdminAccountAdmin(admin.ModelAdmin):
    form = StoreAdminAccountForm
    list_display = ["id", "login", "store", "active", "created_at"]
    list_filter = ["active", "store"]
    search_fields = ["login"]
