from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import LoginSerializer, RegistrationSerializer
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