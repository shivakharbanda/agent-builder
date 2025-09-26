from django.contrib import admin
from .models import CredentialCategory, CredentialType, CredentialField, Credential, CredentialDetail


@admin.register(CredentialCategory)
class CredentialCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'icon', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at', 'created_by']

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class CredentialFieldInline(admin.TabularInline):
    model = CredentialField
    extra = 0
    fields = ['field_name', 'field_type', 'is_required', 'is_secure', 'order', 'placeholder', 'help_text']
    ordering = ['order', 'field_name']


@admin.register(CredentialType)
class CredentialTypeAdmin(admin.ModelAdmin):
    list_display = ['type_name', 'category', 'type_description', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['type_name', 'type_description', 'category__name']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    inlines = [CredentialFieldInline]

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if not instance.pk:  # New instance
                instance.created_by = request.user
            instance.save()
        formset.save_m2m()


@admin.register(CredentialField)
class CredentialFieldAdmin(admin.ModelAdmin):
    list_display = ['credential_type', 'field_name', 'field_type', 'is_required', 'is_secure', 'order', 'is_active']
    list_filter = ['credential_type', 'field_type', 'is_required', 'is_secure', 'is_active']
    search_fields = ['field_name', 'credential_type__type_name']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    ordering = ['credential_type', 'order', 'field_name']

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


class CredentialDetailInline(admin.TabularInline):
    model = CredentialDetail
    extra = 0
    fields = ['field', 'value']
    readonly_fields = ['field']

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('field')


@admin.register(Credential)
class CredentialAdmin(admin.ModelAdmin):
    list_display = ['name', 'user', 'credential_type', 'is_active', 'is_deleted', 'created_at']
    list_filter = ['credential_type', 'is_active', 'is_deleted', 'created_at', 'user']
    search_fields = ['name', 'description', 'user__username', 'credential_type__type_name']
    readonly_fields = ['created_at', 'updated_at', 'created_by']
    inlines = [CredentialDetailInline]

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    def save_formset(self, request, form, formset, change):
        instances = formset.save(commit=False)
        for instance in instances:
            if not instance.pk:  # New instance
                instance.created_by = request.user
            instance.save()
        formset.save_m2m()


@admin.register(CredentialDetail)
class CredentialDetailAdmin(admin.ModelAdmin):
    list_display = ['credential', 'field', 'get_masked_value', 'created_at']
    list_filter = ['field__credential_type', 'field__is_secure', 'created_at']
    search_fields = ['credential__name', 'field__field_name']
    readonly_fields = ['created_at', 'updated_at', 'created_by']

    def get_masked_value(self, obj):
        if obj.field.is_secure:
            return '***MASKED***'
        return obj.value[:50] + '...' if len(obj.value) > 50 else obj.value
    get_masked_value.short_description = 'Value'

    def save_model(self, request, obj, form, change):
        if not change:  # Creating new object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
