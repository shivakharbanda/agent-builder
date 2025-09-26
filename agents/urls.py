from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AgentViewSet, PromptViewSet, ToolViewSet, AgentToolViewSet, CreateAgentCompleteView

router = DefaultRouter()
router.register(r'agents', AgentViewSet)
router.register(r'prompts', PromptViewSet)
router.register(r'tools', ToolViewSet)
router.register(r'agent-tools', AgentToolViewSet)

urlpatterns = [
    path('api/agents/create-complete/', CreateAgentCompleteView.as_view(), name='agent-create-complete'),
    path('api/', include(router.urls)),
]