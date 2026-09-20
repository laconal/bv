from django.conf import settings

from core.jwt import JWTIssuer

store_admin_jwt = JWTIssuer(
    private_key_path=settings.STORE_ADMIN_JWT["PRIVATE_KEY_PATH"],
    public_key_path=settings.STORE_ADMIN_JWT["PUBLIC_KEY_PATH"],
    algorithm=settings.JWT_ALGORITHM,
    access_ttl=settings.STORE_ADMIN_JWT["ACCESS_TOKEN_EXPIRE_SECONDS"],
    refresh_ttl=settings.STORE_ADMIN_JWT["REFRESH_TOKEN_EXPIRE_SECONDS"],
)
