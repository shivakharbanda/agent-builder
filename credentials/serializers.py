from rest_framework import serializers
from django.db import transaction
from .models import CredentialCategory, CredentialType, CredentialField, Credential, CredentialDetail


class CredentialCategorySerializer(serializers.ModelSerializer):
    """Serializer for credential categories"""
    types_count = serializers.SerializerMethodField()

    class Meta:
        model = CredentialCategory
        fields = ['id', 'name', 'description', 'icon', 'types_count', 'is_active']

    def get_types_count(self, obj):
        return obj.credential_types.filter(is_active=True).count()


class CredentialFieldSerializer(serializers.ModelSerializer):
    """Serializer for credential fields - used in dynamic form generation"""
    class Meta:
        model = CredentialField
        fields = [
            'id', 'field_name', 'field_type', 'is_required', 'is_secure',
            'order', 'placeholder', 'help_text'
        ]


class CredentialTypeSerializer(serializers.ModelSerializer):
    """Serializer for credential types"""
    fields = CredentialFieldSerializer(many=True, read_only=True)
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)

    class Meta:
        model = CredentialType
        fields = [
            'id', 'category', 'category_name', 'category_icon', 'type_name', 'type_description',
            'handler_class_name', 'fields', 'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['created_at', 'updated_at', 'category_name', 'category_icon']


class CredentialTypeListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for credential type lists"""
    fields_count = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='category.name', read_only=True)
    category_icon = serializers.CharField(source='category.icon', read_only=True)

    class Meta:
        model = CredentialType
        fields = [
            'id', 'category', 'category_name', 'category_icon', 'type_name',
            'type_description', 'fields_count', 'is_active'
        ]

    def get_fields_count(self, obj):
        return obj.fields.filter(is_active=True).count()


class CredentialDetailSerializer(serializers.ModelSerializer):
    """Serializer for credential details"""
    field_name = serializers.CharField(source='field.field_name', read_only=True)
    field_type = serializers.CharField(source='field.field_type', read_only=True)
    is_secure = serializers.BooleanField(source='field.is_secure', read_only=True)

    class Meta:
        model = CredentialDetail
        fields = ['id', 'field', 'field_name', 'field_type', 'is_secure', 'value']

    def to_representation(self, instance):
        """Mask secure field values in responses"""
        data = super().to_representation(instance)
        if instance.field.is_secure and data['value']:
            data['value'] = '***MASKED***'
        return data


class CredentialSerializer(serializers.ModelSerializer):
    """Main serializer for credentials"""
    details = CredentialDetailSerializer(many=True, read_only=True)
    credential_type_name = serializers.CharField(source='credential_type.type_name', read_only=True)

    class Meta:
        model = Credential
        fields = [
            'id', 'name', 'description', 'credential_type', 'credential_type_name',
            'details', 'created_at', 'updated_at', 'created_by', 'is_active', 'is_deleted'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'credential_type_name']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)


class CredentialListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for credential lists"""
    credential_type_name = serializers.CharField(source='credential_type.type_name', read_only=True)
    details_count = serializers.SerializerMethodField()

    class Meta:
        model = Credential
        fields = [
            'id', 'name', 'description', 'credential_type_name',
            'details_count', 'created_at', 'is_active'
        ]

    def get_details_count(self, obj):
        return obj.details.filter(is_active=True).count()


class CredentialCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating credentials with details in a single request"""
    credential_details = serializers.DictField(write_only=True)

    class Meta:
        model = Credential
        fields = ['name', 'description', 'credential_type', 'credential_details']

    def validate_credential_details(self, value):
        """Validate that all required fields are provided"""
        credential_type_id = self.initial_data.get('credential_type')
        if not credential_type_id:
            raise serializers.ValidationError("credential_type is required")

        try:
            credential_type = CredentialType.objects.get(id=credential_type_id, is_active=True)
        except CredentialType.DoesNotExist:
            raise serializers.ValidationError("Invalid credential_type")

        required_fields = credential_type.fields.filter(is_required=True, is_active=True)

        for field in required_fields:
            if field.field_name not in value or not value[field.field_name]:
                raise serializers.ValidationError(f"Field '{field.field_name}' is required")

        return value

    @transaction.atomic
    def create(self, validated_data):
        credential_details_data = validated_data.pop('credential_details')

        # Set user info
        validated_data['created_by'] = self.context['request'].user
        validated_data['user'] = self.context['request'].user

        # Create the credential
        credential = Credential.objects.create(**validated_data)

        # Create credential details
        credential_type = credential.credential_type
        for field_name, field_value in credential_details_data.items():
            try:
                field = credential_type.fields.get(field_name=field_name, is_active=True)
                CredentialDetail.objects.create(
                    credential=credential,
                    field=field,
                    value=str(field_value),
                    created_by=self.context['request'].user
                )
            except CredentialField.DoesNotExist:
                # Skip unknown fields
                continue

        return credential


class CredentialUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating credentials with details"""
    credential_details = serializers.DictField(write_only=True, required=False)

    class Meta:
        model = Credential
        fields = ['name', 'description', 'credential_details']

    @transaction.atomic
    def update(self, instance, validated_data):
        credential_details_data = validated_data.pop('credential_details', None)

        # Update basic credential info
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Update credential details if provided
        if credential_details_data is not None:
            for field_name, field_value in credential_details_data.items():
                try:
                    field = instance.credential_type.fields.get(field_name=field_name, is_active=True)
                    detail, created = CredentialDetail.objects.get_or_create(
                        credential=instance,
                        field=field,
                        defaults={
                            'value': str(field_value),
                            'created_by': self.context['request'].user
                        }
                    )
                    if not created:
                        detail.value = str(field_value)
                        detail.save()
                except CredentialField.DoesNotExist:
                    # Skip unknown fields
                    continue

        return instance