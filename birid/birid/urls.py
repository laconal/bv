from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/v1/auth/store-admin/", include("stores.urls")),
    path("api/v1/auth/buyer/", include("buyers.urls")),
    path("api/v1/store-admin/", include("stores.admin_urls")),
    path("api/v1/store-admin/", include("products.urls")),
    path("api/v1/store-admin/", include("news.urls")),

    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
