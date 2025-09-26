from django.contrib import admin
from .models import DataSource, Workflow, WorkflowProperties, WorkflowExecution, WorkflowNode, PlaceholderMapping, OutputNode


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


class WorkflowPropertiesInline(admin.StackedInline):
    model = WorkflowProperties
    extra = 0
    fields = ['watermark_start_date', 'watermark_end_date', 'schedule', 'timeout', 'retry_count', 'notification_email']


class WorkflowExecutionInline(admin.TabularInline):
    model = WorkflowExecution
    extra = 0
    fields = ['status', 'started_at', 'completed_at', 'triggered_by']
    readonly_fields = ['started_at', 'completed_at']


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'get_current_status', 'created_by', 'created_at', 'is_active']
    list_filter = ['project', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [WorkflowPropertiesInline, WorkflowExecutionInline, WorkflowNodeInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'project', 'is_active')
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

    def get_current_status(self, obj):
        latest_execution = obj.executions.first()
        return latest_execution.status if latest_execution else 'No executions'
    get_current_status.short_description = 'Current Status'


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


@admin.register(WorkflowProperties)
class WorkflowPropertiesAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'schedule', 'timeout', 'retry_count', 'notification_email', 'created_at']
    list_filter = ['created_at']
    search_fields = ['workflow__name', 'notification_email']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Scheduling', {
            'fields': ('schedule',)
        }),
        ('Watermark Configuration', {
            'fields': ('watermark_start_date', 'watermark_end_date')
        }),
        ('Execution Settings', {
            'fields': ('timeout', 'retry_count')
        }),
        ('Notifications', {
            'fields': ('notification_email',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(WorkflowExecution)
class WorkflowExecutionAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'status', 'triggered_by', 'started_at', 'completed_at', 'created_at']
    list_filter = ['status', 'triggered_by', 'created_at']
    search_fields = ['workflow__name', 'error_message']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Execution Info', {
            'fields': ('workflow', 'status', 'triggered_by')
        }),
        ('Timing', {
            'fields': ('started_at', 'completed_at')
        }),
        ('Results', {
            'fields': ('execution_log', 'error_message'),
            'classes': ('collapse',)
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(OutputNode)
class OutputNodeAdmin(admin.ModelAdmin):
    list_display = ['workflow', 'destination_table', 'created_by', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['workflow__name', 'destination_table']
    readonly_fields = ['created_at', 'updated_at']
