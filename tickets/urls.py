from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TicketViewSet, CategoryViewSet, PriorityViewSet, 
    StatusViewSet, CommentViewSet
)

router = DefaultRouter()
router.register(r'tickets', TicketViewSet, basename='ticket')
router.register(r'categories', CategoryViewSet, basename='category')
router.register(r'priorities', PriorityViewSet, basename='priority')
router.register(r'statuses', StatusViewSet, basename='status')
router.register(r'comments', CommentViewSet, basename='comment')

urlpatterns = [
    path('', include(router.urls)),
]