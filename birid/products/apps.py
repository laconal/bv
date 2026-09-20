from django.apps import AppConfig


class ProductsConfig(AppConfig):
    name = "products"

    def ready(self):
        import pillow_heif

        pillow_heif.register_heif_opener()
