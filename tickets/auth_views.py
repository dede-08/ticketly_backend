from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from .auth_serializers import RegisterSerializer, UserDetailSerializer, ChangePasswordSerializer


class RegisterView(generics.CreateAPIView):
    """vista para registro de usuarios"""
    queryset = User.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        #generar tokens para el nuevo usuario
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
            },
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'usuario registrado exitosamente'
        }, status=status.HTTP_201_CREATED)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """sista para ver y actualizar perfil del usuario"""
    serializer_class = UserDetailSerializer
    permission_classes = (IsAuthenticated,)

    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    """vista para cambiar contraseña"""
    serializer_class = ChangePasswordSerializer
    permission_classes = (IsAuthenticated,)

    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        
        #verificar contraseña actual
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {'old_password': 'contraseña incorrecta'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        #establecer nueva contraseña
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'contraseña actualizada exitosamente'
        }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """vista para cerrar sesión"""
    try:
        refresh_token = request.data.get("refresh")
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()
        return Response({
            'message': 'sesion cerrada exitosamente'
        }, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({
            'error': 'token invalido'
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_info_view(request):
    """vista para obtener información del usuario actual - CORREGIDA"""
    user = request.user
    
    #determinar el rol del usuario
    role = 'Usuario'
    if user.is_superuser:
        role = 'Administrador'
    elif user.is_staff:
        role = 'Staff'
    elif user.groups.exists():
        role = user.groups.first().name
    
    
    data = {
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'is_staff': user.is_staff,
        'is_superuser': user.is_superuser,
        'date_joined': user.date_joined,
        'role': role,
        'groups': [{'id': g.id, 'name': g.name} for g in user.groups.all()],
    }

    print(f"enviando datos de usuario: {user.first_name} {user.last_name}")
    return Response(data, status=status.HTTP_200_OK)