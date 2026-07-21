from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.db import transaction

from .authentication import JWTAuthentication
from users.models import AuthSession
from .serializers import LoginSerializer, RegistrationSerializer, ProfilePatchSerializer
from services import jwt

class RegistrationView(APIView):
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.save()

        return Response(
            {
                'id': user.id,
                'email': user.email,
            },
            status=status.HTTP_201_CREATED,
        )
    
class LoginView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token = jwt.issue_access_token(serializer.validated_data['user'])

        return Response({
            'access_token': token,
            "token_type": "Bearer",
            "expires_in": 3600
        })


class MeView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        return Response(
            {
                "id": user.id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "middle_name": user.middle_name,
                "role": {
                    "code": user.role.code,
                    "name": user.role.name,
                },
            }
        )


class LogoutView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        jti = request.auth['jti']
        session = AuthSession.objects.filter(jti=jti).first()

        session.revoked_at = timezone.now()
        session.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    
class ProfileView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        return Response(
            {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "middle_name": user.middle_name,
            }
        )
    
    def patch(self, request):
        user = request.user
        serializer = ProfilePatchSerializer(
            data=request.data,
            context={"user": request.user},
        )

        serializer.is_valid(raise_exception=True)

        for key in serializer.validated_data:
            setattr(user, key, serializer.validated_data[key])

        user.save()

        return Response(
            {
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "middle_name": user.middle_name,
            }
        )

    @transaction.atomic
    def delete(self, request):
        now = timezone.now()
        user = request.user

        user.is_active = False
        user.deleted_at = now
        user.save()

        sessions = user.auth_sessions.filter(revoked_at=None).update(revoked_at=now)

        return Response(status=status.HTTP_204_NO_CONTENT)