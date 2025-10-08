from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AgentViewSet, PromptViewSet, ToolViewSet, AgentToolViewSet,
    CreateAgentCompleteView, TestAgentView,
    MCPServerViewSet, AgentMCPServerViewSet,
    InternalToolViewSet, AgentInternalToolViewSet
)

router = DefaultRouter()
router.register(r'agents', AgentViewSet)
router.register(r'prompts', PromptViewSet)
router.register(r'tools', ToolViewSet)
router.register(r'agent-tools', AgentToolViewSet)
router.register(r'mcp-servers', MCPServerViewSet)
router.register(r'agent-mcp-servers', AgentMCPServerViewSet)
router.register(r'internal-tools', InternalToolViewSet)
router.register(r'agent-internal-tools', AgentInternalToolViewSet)

urlpatterns = [
    path('api/agents/create-complete/', CreateAgentCompleteView.as_view(), name='agent-create-complete'),
    path('api/agents/<int:pk>/test/', TestAgentView.as_view(), name='agent-test'),
    path('api/', include(router.urls)),
]