from django.urls import path

from .views import (
    BuyerFavoriteProductListView,
    BuyerFavoriteProductView,
    BuyerFavoriteStoreListView,
    BuyerFavoriteStoreView,
    BuyerLoginView,
    BuyerMeView,
    BuyerRefreshView,
)

urlpatterns = [
    path("login", BuyerLoginView.as_view(), name="buyer-login"),
    path("refresh", BuyerRefreshView.as_view(), name="buyer-refresh"),
    path("me", BuyerMeView.as_view(), name="buyer-me"),
    path("favorites/products/get-all", BuyerFavoriteProductListView.as_view(), name="buyer-favorite-products-list"),
    path("favorites/stores/get-all", BuyerFavoriteStoreListView.as_view(), name="buyer-favorite-stores-list"),
    path("favorites/products/<int:product_id>", BuyerFavoriteProductView.as_view(), name="buyer-favorite-product"),
    path("favorites/stores/<int:store_id>", BuyerFavoriteStoreView.as_view(), name="buyer-favorite-store"),
]
