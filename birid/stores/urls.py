from django.urls import path

from .views import StoreAdminLoginView, StoreAdminMeView, StoreAdminRefreshView

urlpatterns = [
    path("login", StoreAdminLoginView.as_view(), name="store-admin-login"),
    path("refresh", StoreAdminRefreshView.as_view(), name="store-admin-refresh"),
    path("me", StoreAdminMeView.as_view(), name="store-admin-me"),
]
