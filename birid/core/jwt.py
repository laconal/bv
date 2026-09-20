from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import jwt


@dataclass(frozen=True)
class JWTIssuer:
    """
    One RSA-signed access/refresh token pair issuer for a single principal
    type (e.g. store admins or buyers). Each principal type gets its own
    instance - and its own keypair - so a token issued for one can never be
    replayed against the other's endpoints.
    """

    private_key_path: str
    public_key_path: str
    algorithm: str
    access_ttl: int
    refresh_ttl: int

    @property
    def private_key(self) -> str:
        return Path(self.private_key_path).read_text()

    @property
    def public_key(self) -> str:
        return Path(self.public_key_path).read_text()

    def create_access_token(self, payload: dict) -> str:
        return self._encode(payload, self.access_ttl, "access")

    def create_refresh_token(self, payload: dict) -> str:
        return self._encode(payload, self.refresh_ttl, "refresh")

    def _encode(self, payload: dict, ttl_seconds: int, token_type: str) -> str:
        to_encode = {
            **payload,
            "type": token_type,
            "exp": datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds),
        }
        return jwt.encode(to_encode, self.private_key, algorithm=self.algorithm)

    def decode(self, token: str) -> dict | None:
        try:
            return jwt.decode(token, self.public_key, algorithms=[self.algorithm])
        except jwt.PyJWTError:
            return None
