"""
Database Node Handler

Handles execution of database query nodes.
Connects to databases and executes SQL queries.
"""

from typing import Any
from .base import BaseNode
from .database_executor import DatabaseExecutor
from credentials.models import Credential


class DatabaseNode(BaseNode):
    """
    Database node handler.

    Executes SQL queries against configured database connections.
    Supports dynamic placeholders for parameterized queries.

    Configuration Required:
        - credential_id (int): ID of database credential
        - query (str): SQL query to execute
        - placeholders (dict, optional): Placeholder values for query

    Outputs:
        List of dictionaries representing query results (table rows)
    """

    node_type = 'database'
    category = 'data_source'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Define dependencies
        self.required_dependencies = ['credential_id', 'query']
        self.optional_dependencies = ['placeholders']

    def validate(self) -> bool:
        """
        Validate database node configuration.

        Checks:
        - credential_id is present and valid
        - credential exists and is active
        - credential is RDBMS type
        - query is present and non-empty

        Returns:
            bool: True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        config = self.configuration

        # Check credential_id is provided
        credential_id = config.get('credential_id')
        if not credential_id:
            raise ValueError("credential_id is required")

        # Verify credential exists and is active
        try:
            credential = Credential.objects.get(
                id=credential_id,
                is_active=True,
                is_deleted=False
            )
        except Credential.DoesNotExist:
            raise ValueError(f"Credential with ID {credential_id} not found or inactive")

        # Verify credential is RDBMS type
        category_name = credential.credential_type.category.name
        if category_name != 'RDBMS':
            raise ValueError(
                f"Credential must be RDBMS type, got '{category_name}'. "
                f"Database node requires relational database credentials."
            )

        # Check query is provided
        query = config.get('query')
        if not query:
            raise ValueError("query is required")

        # Validate query is not just whitespace
        if not query.strip():
            raise ValueError("query cannot be empty or whitespace only")

        return True

    def execute(self, input_data: Any = None) -> Any:
        """
        Execute SQL query and return results.

        This method handles Django-specific concerns (fetching credential),
        then delegates to the pure Python DatabaseExecutor for actual execution.

        Args:
            input_data: Not used (database is a source node)

        Returns:
            List[Dict]: Query results as list of dictionaries

        Raises:
            ValueError: If credential not found
            Exception: If database connection or query execution fails
        """
        config = self.configuration

        try:
            # 1. Fetch credential from Django database
            credential_id = config.get('credential_id')
            credential = Credential.objects.get(
                id=credential_id,
                is_active=True,
                is_deleted=False
            )

            # 2. Extract database connection information
            db_type = credential.credential_type.type_name
            connection_details = credential.get_connection_details()

            # 3. Extract query configuration
            query = config.get('query')
            placeholders = config.get('placeholders', {})

            # 4. Execute query using pure Python executor
            results = DatabaseExecutor.execute_query(
                db_type=db_type,
                connection_details=connection_details,
                query=query,
                placeholders=placeholders
            )

            return results

        except Credential.DoesNotExist:
            raise ValueError(
                f"Credential with ID {credential_id} not found. "
                f"Please verify the credential exists and is active."
            )
        except ValueError as e:
            # DatabaseExecutor raises ValueError for unsupported db types
            raise ValueError(f"Database configuration error: {str(e)}")
        except Exception as e:
            # Re-raise with additional context for debugging
            credential_name = credential.name if 'credential' in locals() else f"ID {credential_id}"
            query_preview = query[:100] + "..." if len(query) > 100 else query
            raise Exception(
                f"Database query execution failed for credential '{credential_name}'. "
                f"Query: {query_preview}. Error: {str(e)}"
            )
