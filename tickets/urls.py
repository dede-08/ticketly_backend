from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import (
    TicketViewSet, CategoryViewSet, PriorityViewSet, 
    StatusViewSet, CommentViewSet
)
from .auth_views import (
    RegisterView, UserProfileView, ChangePasswordView, 
    logout_view, user_info_view
)

router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'priorities', PriorityViewSet, basename='priority')
router.register(r'statuses', StatusViewSet, basename='status')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    #authentication endpoints
    path('auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/logout/', logout_view, name='logout'),
    path('auth/user/', user_info_view, name='user_info'),
    path('auth/profile/', UserProfileView.as_view(), name='user_profile'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    #router URLs
    path('', include(router.urls)),
]