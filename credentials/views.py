from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

from .models import CredentialCategory, CredentialType, CredentialField, Credential, CredentialDetail
from .serializers import (
    CredentialCategorySerializer, CredentialTypeSerializer, CredentialTypeListSerializer,
    CredentialFieldSerializer, CredentialSerializer, CredentialListSerializer,
    CredentialCreateSerializer, CredentialUpdateSerializer
)


class CredentialCategoryViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for credential categories - read-only for users"""
    queryset = CredentialCategory.objects.filter(is_active=True)
    serializer_class = CredentialCategorySerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']

    @action(detail=True, methods=['get'])
    def types(self, request, pk=None):
        """Get all credential types for this category"""
        category = self.get_object()
        types = CredentialType.objects.filter(
            category=category,
            is_active=True
        ).order_by('type_name')
        serializer = CredentialTypeListSerializer(types, many=True)
        return Response(serializer.data)


class CredentialTypeViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet for credential types - read-only for users"""
    queryset = CredentialType.objects.filter(is_active=True)
    serializer_class = CredentialTypeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category']
    search_fields = ['type_name', 'type_description', 'category__name']
    ordering_fields = ['type_name', 'created_at']
    ordering = ['category__name', 'type_name']

    def get_serializer_class(self):
        if self.action == 'list':
            return CredentialTypeListSerializer
        return CredentialTypeSerializer

    @action(detail=True, methods=['get'])
    def fields(self, request, pk=None):
        """Get all fields for this credential type - used for dynamic form generation"""
        credential_type = self.get_object()
        fields = CredentialField.objects.filter(
            credential_type=credential_type,
            is_active=True
        ).order_by('order', 'field_name')
        serializer = CredentialFieldSerializer(fields, many=True)
        return Response(serializer.data)


class CredentialViewSet(viewsets.ModelViewSet):
    """ViewSet for user credentials"""
    serializer_class = CredentialSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['credential_type', 'is_active', 'is_deleted']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        """Filter credentials by current user and exclude deleted ones by default"""
        queryset = Credential.objects.filter(user=self.request.user)

        # By default, exclude deleted credentials unless specifically requested
        include_deleted = self.request.query_params.get('include_deleted', 'false').lower()
        if include_deleted not in ['true', '1']:
            queryset = queryset.filter(is_deleted=False)

        return queryset

    def get_serializer_class(self):
        if self.action == 'list':
            return CredentialListSerializer
        elif self.action == 'create':
            return CredentialCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return CredentialUpdateSerializer
        return CredentialSerializer

    def perform_destroy(self, instance):
        """Soft delete instead of hard delete"""
        instance.is_deleted = True
        instance.save()

    @action(detail=True, methods=['post'])
    def restore(self, request, pk=None):
        """Restore a soft-deleted credential"""
        credential = self.get_object()
        credential.is_deleted = False
        credential.save()

        serializer = self.get_serializer(credential)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def connection_details(self, request, pk=None):
        """Get connection details for this credential (masked secure fields)"""
        credential = self.get_object()
        details = credential.get_connection_details()

        # Mask secure fields
        for detail in credential.details.filter(field__is_secure=True):
            if detail.field.field_name in details:
                details[detail.field.field_name] = '***MASKED***'

        return Response({
            'credential_id': credential.id,
            'credential_name': credential.name,
            'credential_type': credential.credential_type.type_name,
            'details': details
        })

    @action(detail=False, methods=['get'])
    def types(self, request):
        """Get available credential types for this user"""
        types = CredentialType.objects.filter(is_active=True)
        serializer = CredentialTypeListSerializer(types, many=True)
        return Response(serializer.data)
