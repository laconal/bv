from drf_spectacular.extensions import OpenApiAuthenticationExtension

from core.authentication import BaseJWTAuthentication

from .models import StoreAdmin
from .security import store_admin_jwt


class StoreAdminJWTAuthentication(BaseJWTAuthentication):
    issuer = store_admin_jwt
    model = StoreAdmin


class StoreAdminJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = StoreAdminJWTAuthentication
    name = "StoreAdminBearerAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
