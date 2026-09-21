from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),

    path("api/v1/stores/", include("stores.urls")),
    path("api/v1/stores/", include("stores.admin_urls")),
    path("api/v1/stores/", include("products.urls")),
    path("api/v1/stores/", include("news.urls")),
    path("api/v1/stores/", include("orders.urls")),
    path("api/v1/stores/reports/", include("products.report_urls")),

    path("api/v1/customers/", include("buyers.urls")),
    path("api/v1/customers/", include("orders.customer_urls")),

    path("api/v1/public/", include("stores.public_urls")),
    path("api/v1/public/", include("products.public_urls")),
    path("api/v1/public/", include("news.public_urls")),

    path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
