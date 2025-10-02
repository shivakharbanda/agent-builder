"""
Database Executor

Pure Python module for executing database queries using dq_db_manager.
No Django dependencies - can be used in Django, FastAPI, or standalone scripts.

This module provides a clean separation between business logic and framework-specific code,
making it reusable across different contexts (workflow execution, agentic query generation, etc.).
"""

from typing import Any, Dict, Optional, List
from dq_db_manager.database_factory import DatabaseFactory



class DatabaseExecutor:
    """
    Pure Python database executor - framework agnostic.

    Handles database query execution using the dq_db_manager package.
    Can be used from Django views, FastAPI endpoints, or standalone scripts.
    """

    @staticmethod
    def execute_query(
        db_type: str,
        connection_details: Dict[str, Any],
        query: str,
        placeholders: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Execute SQL query using dq_db_manager.

        Args:
            db_type: Database type (e.g., "PostgreSQL", "MySQL") - will be lowercased
            connection_details: Dict with database connection parameters
                               (e.g., {host, port, user, password, database})
            query: SQL query string with optional {{placeholder}} syntax
            placeholders: Optional dict mapping placeholder names to values
                         (e.g., {"start_date": "2024-01-01", "status": "active"})

        Returns:
            List of dictionaries representing query results (table rows)

        Raises:
            ValueError: If db_type is not supported by DatabaseFactory
            Exception: If database connection or query execution fails

        Example:
            >>> results = DatabaseExecutor.execute_query(
            ...     db_type="PostgreSQL",
            ...     connection_details={
            ...         "host": "localhost",
            ...         "port": 5432,
            ...         "user": "admin",
            ...         "password": "secret",
            ...         "database": "mydb"
            ...     },
            ...     query="SELECT * FROM users WHERE status = {{status}}",
            ...     placeholders={"status": "active"}
            ... )
        """
        try:
            # Normalize database type for DatabaseFactory (lowercase)
            db_type_normalized = db_type.lower()

            # Replace placeholders if provided
            final_query = query
            if placeholders:
                final_query = DatabaseExecutor.replace_placeholders(query, placeholders)

            # Get database handler from factory
            handler = DatabaseFactory.get_database_handler(db_type_normalized, connection_details)

            # Execute query using the handler's connection handler
            results = handler.connection_handler.execute_query(final_query, params=None)

            return results

        except ValueError as e:
            # DatabaseFactory raises ValueError for unsupported db types
            raise ValueError(f"Unsupported database type '{db_type}': {str(e)}")
        except Exception as e:
            # Catch all other errors and provide context
            raise Exception(f"Database query execution failed: {str(e)}")

    @staticmethod
    def replace_placeholders(query: str, placeholders: Dict[str, Any]) -> str:
        """
        Replace {{placeholder}} syntax with actual values.

        Replaces all occurrences of {{key}} in the query with the corresponding
        value from the placeholders dictionary.

        Args:
            query: SQL query with {{placeholder}} markers
            placeholders: Dict mapping placeholder names to their values

        Returns:
            Query string with all placeholders replaced

        Example:
            >>> query = "SELECT * FROM users WHERE created_at > {{start_date}} AND status = {{status}}"
            >>> placeholders = {"start_date": "2024-01-01", "status": "active"}
            >>> DatabaseExecutor.replace_placeholders(query, placeholders)
            "SELECT * FROM users WHERE created_at > 2024-01-01 AND status = active"
        """
        result = query
        for key, value in placeholders.items():
            # Replace {{key}} with string representation of value
            placeholder_marker = f"{{{{{key}}}}}"
            result = result.replace(placeholder_marker, str(value))

        return result

    @staticmethod
    def validate_placeholders(query: str, placeholders: Dict[str, Any]) -> List[str]:
        """
        Validate that all placeholders in the query are provided.

        Args:
            query: SQL query with {{placeholder}} markers
            placeholders: Dict of provided placeholder values

        Returns:
            List of missing placeholder names (empty if all provided)

        Example:
            >>> query = "SELECT * FROM users WHERE created_at > {{start_date}} AND status = {{status}}"
            >>> placeholders = {"start_date": "2024-01-01"}
            >>> DatabaseExecutor.validate_placeholders(query, placeholders)
            ['status']
        """
        import re

        # Find all {{placeholder}} patterns in query
        placeholder_pattern = r'\{\{(\w+)\}\}'
        found_placeholders = re.findall(placeholder_pattern, query)

        # Check which ones are missing
        missing = [p for p in found_placeholders if p not in placeholders]

        return missing
