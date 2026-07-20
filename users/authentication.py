import uuid

import jwt
from django.conf import settings
from django.utils import timezone
from rest_framework import authentication
from rest_framework.exceptions import AuthenticationFailed

from .models import AuthSession


class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request)

        if not auth_header:
            return None

        auth_parts = auth_header.split()
        if len(auth_parts) != 2 or auth_parts[0].lower() != b"bearer":
            raise AuthenticationFailed("Invalid authorization header format.")

        try:
            token = auth_parts[1].decode("utf-8")
            payload = jwt.decode(
                token,
                key=settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            jti = uuid.UUID(payload["jti"])
            user_id = payload["sub"]
            token_type = payload["type"]
        except (
            jwt.InvalidTokenError,
            KeyError,
            TypeError,
            UnicodeDecodeError,
            ValueError,
        ):
            raise AuthenticationFailed("Invalid or expired token.")

        session = (
            AuthSession.objects.select_related("user")
            .filter(jti=jti)
            .first()
        )

        if (
            not session
            or str(session.user_id) != user_id
            or session.revoked_at is not None
            or session.expires_at <= timezone.now()
            or token_type != "access"
            or not session.user.is_active
            or session.user.deleted_at is not None
        ):
            raise AuthenticationFailed("Invalid or expired token.")

        return session.user, payload

    def authenticate_header(self, request):
        return "Bearer"
