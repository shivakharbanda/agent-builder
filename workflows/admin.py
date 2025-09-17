from django.contrib import admin
from .models import DataSource, Workflow, WorkflowNode, PlaceholderMapping, OutputNode


class WorkflowNodeInline(admin.TabularInline):
    model = WorkflowNode
    extra = 0
    fields = ['node_type', 'position', 'agent', 'data_source']


class PlaceholderMappingInline(admin.TabularInline):
    model = PlaceholderMapping
    extra = 0
    fields = ['placeholder_name', 'data_column', 'transformation']


@admin.register(DataSource)
class DataSourceAdmin(admin.ModelAdmin):
    list_display = ['name', 'source_type', 'load_mode', 'created_by', 'created_at', 'is_active']
    list_filter = ['source_type', 'load_mode', 'is_active', 'created_at']
    search_fields = ['name', 'table_name']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'source_type', 'table_name', 'is_active')
        }),
        ('Load Configuration', {
            'fields': ('load_mode', 'watermark_start_date', 'watermark_end_date')
        }),
        ('Connection Settings', {
            'fields': ('connection_config',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'status', 'created_by', 'created_at', 'is_active']
    list_filter = ['status', 'project', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [WorkflowNodeInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'project', 'status', 'is_active')
        }),
        ('Configuration', {
            'fields': ('configuration',),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkflowNode)
class WorkflowNodeAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'node_type', 'position', 'agent', 'data_source', 'is_active']
    list_filter = ['node_type', 'is_active', 'created_at']
    search_fields = ['workflow__name']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PlaceholderMappingInline]


@admin.register(PlaceholderMapping)
class PlaceholderMappingAdmin(admin.ModelAdmin):
    list_display = ['workflow_node', 'placeholder_name', 'data_column', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['placeholder_name', 'data_column']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(OutputNode)
class OutputNodeAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'destination_table', 'created_by', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['workflow__name', 'destination_table']
    readonly_fields = ['created_at', 'updated_at']
