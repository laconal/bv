from drf_spectacular.extensions import OpenApiAuthenticationExtension

from core.authentication import BaseJWTAuthentication

from .models import Buyer
from .security import buyer_jwt


class BuyerJWTAuthentication(BaseJWTAuthentication):
    issuer = buyer_jwt
    model = Buyer


class BuyerJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = BuyerJWTAuthentication
    name = "BuyerBearerAuth"

    def get_security_definition(self, auto_schema):
        return {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
