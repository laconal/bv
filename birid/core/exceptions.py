import logging

from django.db import IntegrityError
from rest_framework import exceptions, status
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

logger = logging.getLogger(__name__)


class InvalidCredentials(exceptions.APIException):
    """
    401 for a failed login/refresh. Deliberately not an AuthenticationFailed
    subclass - DRF coerces that to 403 on views with no authentication_classes
    (no WWW-Authenticate header to justify a 401), which is wrong for a login
    endpoint's own credential check.
    """

    status_code = status.HTTP_401_UNAUTHORIZED
    default_detail = "Incorrect login or password"
    default_code = "invalid_credentials"


# Postgres SQLSTATE -> (http status, error code, detail). `store` is injected
# server-side (never a serializer field - see StoreScopedModelViewSet), so
# DRF can't build its usual UniqueValidator/UniqueTogetherValidator for
# constraints involving it - duplicates only surface as a raw IntegrityError
# at the DB layer. This maps that (and other constraint violations) to a
# proper response instead of an unhandled 500.
_SQLSTATE_MAP = {
    "23505": (status.HTTP_409_CONFLICT, "unique_violation", "A record with this value already exists."),
    "23503": (status.HTTP_404_NOT_FOUND, "foreign_key_violation", "Referenced record was not found."),
    "23502": (status.HTTP_409_CONFLICT, "not_null_violation", "A required field is missing."),
    "23514": (status.HTTP_409_CONFLICT, "check_violation", "This value violates a database constraint."),
}


def custom_exception_handler(exc, context):
    response = drf_exception_handler(exc, context)
    if response is not None:
        return response

    if isinstance(exc, IntegrityError):
        cause = exc.__cause__
        sqlstate = getattr(cause, "sqlstate", None)
        http_status, code, detail = _SQLSTATE_MAP.get(
            sqlstate, (status.HTTP_409_CONFLICT, "integrity_error", "Database integrity constraint violated."),
        )
        constraint_name = getattr(getattr(cause, "diag", None), "constraint_name", None)
        logger.warning("IntegrityError (sqlstate=%s, constraint=%s): %s", sqlstate, constraint_name, exc)
        return Response({"detail": detail, "code": code}, status=http_status)

    return None
