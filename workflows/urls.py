from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    DataSourceViewSet, WorkflowViewSet, WorkflowNodeViewSet,
    PlaceholderMappingViewSet, OutputNodeViewSet
)

router = DefaultRouter()
router.register(r'data-sources', DataSourceViewSet)
router.register(r'workflows', WorkflowViewSet)
router.register(r'workflow-nodes', WorkflowNodeViewSet)
router.register(r'placeholder-mappings', PlaceholderMappingViewSet)
router.register(r'output-nodes', OutputNodeViewSet)

urlpatterns = [
    path('api/', include(router.urls)),
]