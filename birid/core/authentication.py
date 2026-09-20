from rest_framework import authentication, exceptions

from core.jwt import JWTIssuer


class BaseJWTAuthentication(authentication.BaseAuthentication):
    """
    Subclass per principal type, setting `issuer` (a JWTIssuer bound to that
    type's own RSA keypair) and `model` (its AbstractAuthAccount subclass).
    request.user is set to the loaded account, request.auth to the raw
    token payload (e.g. to read store_id off a StoreAdmin's token).
    """

    issuer: JWTIssuer
    model = None
    keyword = "Bearer"

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).decode("utf-8")
        if not auth_header:
            return None

        parts = auth_header.split()
        if len(parts) != 2 or parts[0] != self.keyword:
            return None

        payload = self.issuer.decode(parts[1])
        if payload is None:
            raise exceptions.AuthenticationFailed("Invalid or expired token")
        if payload.get("type") != "access":
            raise exceptions.AuthenticationFailed("Invalid token type")

        account_id = payload.get("id")
        if account_id is None:
            raise exceptions.AuthenticationFailed("Invalid token payload")

        try:
            account = self.model.objects.get(id=account_id)
        except self.model.DoesNotExist:
            raise exceptions.AuthenticationFailed("Account not found")

        if not account.active:
            raise exceptions.AuthenticationFailed("Account is inactive")

        return (account, payload)

    def authenticate_header(self, request):
        return self.keyword
