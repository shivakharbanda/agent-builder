from django.contrib import admin
from .models import Agent, Prompt, Tool, AgentTool


class PromptInline(admin.TabularInline):
    model = Prompt
    extra = 0
    fields = ['prompt_type', 'content', 'placeholders']


class AgentToolInline(admin.TabularInline):
    model = AgentTool
    extra = 0
    fields = ['tool', 'configuration']


@admin.register(Agent)
class AgentAdmin(admin.ModelAdmin):
    list_display = ['name', 'project', 'return_type', 'created_by', 'created_at', 'is_active']
    list_filter = ['return_type', 'project', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']
    inlines = [PromptInline, AgentToolInline]
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description', 'project', 'return_type', 'schema_definition', 'is_active')
        }),
        ('Audit Information', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Prompt)
class PromptAdmin(admin.ModelAdmin):
    list_display = ['agent', 'prompt_type', 'created_at', 'is_active']
    list_filter = ['prompt_type', 'is_active', 'created_at']
    search_fields = ['agent__name', 'content']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Tool)
class ToolAdmin(admin.ModelAdmin):
    list_display = ['name', 'tool_type', 'created_by', 'created_at', 'is_active']
    list_filter = ['tool_type', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AgentTool)
class AgentToolAdmin(admin.ModelAdmin):
    list_display = ['agent', 'tool', 'created_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    readonly_fields = ['created_at', 'updated_at']
