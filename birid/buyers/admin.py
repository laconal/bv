from django import forms
from django.contrib import admin

from .models import Buyer


class BuyerAccountForm(forms.ModelForm):
    password = forms.CharField(
        widget=forms.PasswordInput, required=False,
        help_text="Leave blank to keep the current password.",
    )

    class Meta:
        model = Buyer
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


@admin.register(Buyer)
class BuyerAccountAdmin(admin.ModelAdmin):
    form = BuyerAccountForm
    list_display = ["id", "login", "last_name", "first_name", "city", "age", "gender", "active", "created_at"]
    list_filter = ["active", "gender"]
    search_fields = ["login", "last_name", "first_name", "city"]
    readonly_fields = ["avatar_photo_processed", "avatar_processing_status"]
