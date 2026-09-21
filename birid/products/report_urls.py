from django.urls import path

from .reports import (
    MostFavoritedProductsReportView,
    MostPopularCategoriesReportView,
    MostViewedProductsReportView,
    StoreReportSummaryView,
)

urlpatterns = [
    path("summary", StoreReportSummaryView.as_view(), name="store-report-summary"),
    path("most-viewed-products", MostViewedProductsReportView.as_view(), name="store-report-most-viewed-products"),
    path(
        "most-favorited-products",
        MostFavoritedProductsReportView.as_view(),
        name="store-report-most-favorited-products",
    ),
    path(
        "most-popular-categories",
        MostPopularCategoriesReportView.as_view(),
        name="store-report-most-popular-categories",
    ),
]
