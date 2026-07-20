import uuid
from datetime import timedelta

import jwt
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from users.models import AuthSession


@transaction.atomic
def issue_access_token(user) -> str:
    now = timezone.now()

    expires_at = now + timedelta(
        minutes=settings.JWT_ACCESS_TTL_MINUTES
    )

    jti = uuid.uuid4()

    payload = {
        "sub": str(user.pk),
        "jti": str(jti),
        "iat": now,
        "exp": expires_at,
        "type": "access",
    }

    token = jwt.encode(
        payload=payload,
        key=settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )

    AuthSession.objects.create(
        user=user,
        jti=jti,
        expires_at=expires_at,
    )

    return token