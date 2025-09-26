from django.db import models
from common.models import BaseModel
from django.contrib.auth import get_user_model

User = get_user_model()


class CredentialCategory(BaseModel):
    """
    Categories for organizing credential types (e.g., LLM, Database, API, etc.)

    Attributes:
        name: Category name (e.g., "LLM", "Database", "API")
        description: Description of the category
        icon: Optional icon identifier for UI
    """
    name = models.CharField(max_length=50, unique=True)
    description = models.TextField()
    icon = models.CharField(max_length=100, blank=True, help_text="Icon identifier for UI")

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'credentials_credential_category'
        ordering = ['name']
        verbose_name_plural = 'Credential Categories'


class CredentialType(BaseModel):
    """
    Represents a type of credential/service (e.g., OpenAI API, Gemini API, PostgreSQL) supported by the system.

    Attributes:
        category: The category this credential type belongs to (LLM, Database, etc.)
        type_name: A unique name for the credential type.
        type_description: A detailed description of this credential type.
        handler_class_name: Optional class name for future extensibility.
    """
    category = models.ForeignKey(CredentialCategory, on_delete=models.CASCADE, related_name='credential_types')
    type_name = models.CharField(max_length=100, unique=True)
    type_description = models.TextField()
    handler_class_name = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.type_name

    class Meta:
        db_table = 'credentials_credential_type'
        ordering = ['category__name', 'type_name']


class CredentialField(BaseModel):
    """
    Defines the fields (configuration options) required for a credential type.

    Attributes:
        credential_type: The type of credential to which this field belongs.
        field_name: The name of the configuration field.
        field_type: The data type/input type of the field (e.g., text, password, url).
        is_required: A boolean flag indicating if this field is required.
        is_secure: A boolean flag indicating if this field should be stored securely.
        order: Display order for form generation.
        placeholder: Placeholder text for the field.
        help_text: Help text to display with the field.
    """
    FIELD_TYPE_CHOICES = [
        ('text', 'Text'),
        ('password', 'Password'),
        ('url', 'URL'),
        ('email', 'Email'),
        ('number', 'Number'),
        ('textarea', 'Textarea'),
        ('select', 'Select'),
        ('checkbox', 'Checkbox'),
    ]

    credential_type = models.ForeignKey(CredentialType, on_delete=models.CASCADE, related_name='fields')
    field_name = models.CharField(max_length=100)
    field_type = models.CharField(max_length=100, choices=FIELD_TYPE_CHOICES, default='text')
    is_required = models.BooleanField(default=True)
    is_secure = models.BooleanField(default=False)
    order = models.IntegerField(default=0)
    placeholder = models.CharField(max_length=255, blank=True)
    help_text = models.TextField(blank=True)

    def __str__(self):
        return f"{self.credential_type.type_name} - {self.field_name}"

    class Meta:
        db_table = 'credentials_credential_field'
        ordering = ['credential_type', 'order', 'field_name']
        unique_together = ['credential_type', 'field_name']


class Credential(BaseModel):
    """
    Represents an instance of a credential configured by a user.

    Attributes:
        user: The user who configured this credential.
        credential_type: The type of this credential.
        name: A user-defined name for this credential.
        description: A user-defined description for this credential.
        is_deleted: A boolean flag indicating if this credential is marked as deleted.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='credentials')
    credential_type = models.ForeignKey(CredentialType, on_delete=models.CASCADE, related_name='credentials')
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_deleted = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} ({self.credential_type.type_name})"

    def get_connection_details(self):
        """
        Collects the connection details from CredentialDetail instances.
        """
        details = {detail.field.field_name: detail.value for detail in self.details.all()}
        return details

    class Meta:
        db_table = 'credentials_credential'
        ordering = ['-created_at']
        unique_together = ['user', 'name']


class CredentialDetail(BaseModel):
    """
    Stores the values for the fields defined in CredentialField for each credential instance.

    Attributes:
        credential: The credential instance to which these details belong.
        field: The field for which the value is being stored.
        value: The actual value for the field (encrypted for secure fields).
    """
    credential = models.ForeignKey(Credential, on_delete=models.CASCADE, related_name='details')
    field = models.ForeignKey(CredentialField, on_delete=models.CASCADE, related_name='details')
    value = models.TextField()

    def __str__(self):
        return f'{self.credential.name} - {self.field.field_name}'

    class Meta:
        db_table = 'credentials_credential_detail'
        unique_together = ['credential', 'field']
