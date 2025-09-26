from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CredentialCategoryViewSet, CredentialTypeViewSet, CredentialViewSet

router = DefaultRouter()
router.register(r'categories', CredentialCategoryViewSet, basename='credential-category')
router.register(r'types', CredentialTypeViewSet, basename='credential-type')
router.register(r'credentials', CredentialViewSet, basename='credential')

urlpatterns = [
    path('', include(router.urls)),
]