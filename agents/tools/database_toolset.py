"""
Database Toolset

A toolset providing database query and metadata capabilities.
Works with any RDBMS credential (PostgreSQL, MySQL, etc.) via dq_db_manager factory pattern.
"""

from typing import Any, Dict, List, Optional
from asgiref.sync import sync_to_async
from credentials.models import Credential
from .base import BaseTool


class DatabaseToolset(BaseTool):
    """
    Database toolset for AI agents.

    Provides three tools:
    1. get_schema_summary() - List all tables with their columns
    2. get_table_details(table_name) - Detailed schema for a specific table
    3. execute_query(sql_query) - Execute SELECT queries (read-only)

    The toolset automatically detects the database type from the credential
    and uses the appropriate handler via dq_db_manager's DatabaseFactory.

    Example Usage:
        credential = Credential.objects.get(name='My PostgreSQL DB')
        toolset = DatabaseToolset.get_pydantic_tool(credential)
        agent = PydanticAgent(model=llm, tools=[toolset])
    """

    # Tool metadata
    tool_name = "database_toolset"
    display_name = "Database Toolset"
    description = (
        "Access database schema information and execute SQL queries. "
        "Includes tools to discover tables, get table details, and run SELECT queries. "
        "Supports PostgreSQL, MySQL, and other RDBMS databases."
    )
    requires_credential = True
    required_credential_type = None  # Works with any RDBMS credential
    category = "database"

    # Input/output schemas for documentation
    input_schema = {
        "type": "object",
        "description": "Database toolset (returns multiple tools)",
        "properties": {}
    }

    output_schema = {
        "type": "object",
        "description": "Various outputs depending on which tool is called",
        "properties": {}
    }

    @classmethod
    async def execute(cls, credential: Optional[Credential], **kwargs) -> Any:
        """
        Not used for toolsets - use get_pydantic_tool() instead.

        Toolsets return a FunctionToolset object containing multiple tools,
        not a single execute function.
        """
        raise NotImplementedError(
            "DatabaseToolset uses get_pydantic_tool() to return a toolset. "
            "Do not call execute() directly."
        )

    @classmethod
    def get_pydantic_tool(cls, credential: Optional[Credential]):
        """
        Create PydanticAI FunctionToolset with database tools.

        The credential is captured in the closure and used by all tools.
        The database type is auto-detected from the credential type.

        Args:
            credential: RDBMS credential (PostgreSQL, MySQL, etc.)

        Returns:
            FunctionToolset: Toolset with 3 database tools

        Raises:
            ValueError: If credential is invalid or database type unsupported
        """
        from pydantic_ai.toolsets import FunctionToolset
        from dq_db_manager.database_factory import DatabaseFactory

        # Validate credential
        if not credential:
            raise ValueError("Database toolset requires a credential")

        # Get database type and connection details
        db_type = credential.credential_type.type_name

        # Get connection details synchronously
        connection_details = credential.get_connection_details()

        # Validate it's likely an RDBMS credential
        # (dq_db_manager will fail gracefully if not supported)
        if not connection_details:
            raise ValueError(
                f"Credential '{credential.name}' has no connection details. "
                f"Please verify the credential is properly configured."
            )

        # Create toolset
        toolset = FunctionToolset()

        # Tool 1: Get schema summary
        @toolset.tool
        async def get_schema_summary() -> Dict[str, Any]:
            """
            Get a summary of all tables in the database with their columns.

            Returns a list of all tables with column names and types.
            Use this to understand what data is available in the database.

            Returns:
                dict: Database name and list of tables with columns
                    {
                        "database": "database_name",
                        "tables": [
                            {
                                "table_name": "users",
                                "table_type": "BASE TABLE",
                                "columns": [
                                    {"column_name": "id", "data_type": "integer"},
                                    {"column_name": "email", "data_type": "varchar"}
                                ]
                            }
                        ]
                    }
            """
            try:
                # Get database handler (sync operation)
                def _get_schema():
                    handler = DatabaseFactory.get_database_handler(
                        db_type.lower(),
                        connection_details
                    )

                    # Extract all tables
                    tables = handler.metadata_extractor.extract_table_details(
                        return_as_dict=True
                    )

                    # For each table, get columns
                    for table in tables:
                        table_name = table['table_name']
                        columns = handler.metadata_extractor.extract_column_details(
                            table_name=table_name,
                            return_as_dict=True
                        )
                        table['columns'] = columns

                    return {
                        "database": connection_details.get('database', 'unknown'),
                        "tables": tables
                    }

                # Run sync function in thread pool
                result = await sync_to_async(_get_schema)()
                return result

            except ValueError as e:
                raise ValueError(
                    f"Database type '{db_type}' is not supported by dq_db_manager. "
                    f"Error: {str(e)}"
                )
            except Exception as e:
                raise Exception(
                    f"Failed to get schema summary for database '{connection_details.get('database')}'. "
                    f"Error: {str(e)}"
                )

        # Tool 2: Get table details
        @toolset.tool
        async def get_table_details(table_name: str) -> Dict[str, Any]:
            """
            Get detailed schema information for a specific table.

            Returns columns, data types, constraints, and indexes for the table.
            Use this when you need to understand the structure of a specific table.

            Args:
                table_name: Name of the table to inspect

            Returns:
                dict: Detailed table schema
                    {
                        "table_name": "users",
                        "columns": [
                            {
                                "column_name": "id",
                                "data_type": "integer",
                                "is_nullable": "NO",
                                "column_default": "nextval(...)"
                            }
                        ],
                        "constraints": [
                            {"constraint_name": "users_pkey", "constraint_type": "PRIMARY KEY"}
                        ],
                        "indexes": [
                            {"index_name": "users_pkey", "index_definition": "CREATE UNIQUE INDEX..."}
                        ]
                    }
            """
            if not table_name or not table_name.strip():
                raise ValueError("table_name is required and cannot be empty")

            try:
                def _get_details():
                    handler = DatabaseFactory.get_database_handler(
                        db_type.lower(),
                        connection_details
                    )

                    # Extract detailed metadata for specific table
                    columns = handler.metadata_extractor.extract_column_details(
                        table_name=table_name,
                        return_as_dict=True
                    )

                    constraints = handler.metadata_extractor.extract_constraints_details(
                        table_name=table_name,
                        return_as_dict=True
                    )

                    indexes = handler.metadata_extractor.extract_index_details(
                        table_name=table_name,
                        return_as_dict=True
                    )

                    return {
                        "table_name": table_name,
                        "columns": columns,
                        "constraints": constraints,
                        "indexes": indexes
                    }

                result = await sync_to_async(_get_details)()

                # Check if table exists (no columns = table not found)
                if not result['columns']:
                    raise ValueError(
                        f"Table '{table_name}' not found in database. "
                        f"Use get_schema_summary() to see available tables."
                    )

                return result

            except ValueError as e:
                # Re-raise ValueError as-is (user-facing errors)
                raise e
            except Exception as e:
                raise Exception(
                    f"Failed to get details for table '{table_name}'. "
                    f"Error: {str(e)}"
                )

        # Tool 3: Execute query
        @toolset.tool
        async def execute_query(sql_query: str) -> List[Dict[str, Any]]:
            """
            Execute a SELECT query and return results.

            Only SELECT queries are allowed (read-only). Results are limited to 100 rows.
            Use this to retrieve data from the database based on your analysis.

            Args:
                sql_query: SQL SELECT query to execute

            Returns:
                list: Query results as list of dictionaries (max 100 rows)
                    [
                        {"id": 1, "email": "user@example.com", "created_at": "2024-01-01"},
                        {"id": 2, "email": "admin@example.com", "created_at": "2024-01-02"}
                    ]
            """
            if not sql_query or not sql_query.strip():
                raise ValueError("sql_query is required and cannot be empty")

            # Safety check: only allow SELECT queries
            query_upper = sql_query.strip().upper()
            if not query_upper.startswith('SELECT'):
                raise ValueError(
                    "Only SELECT queries are allowed. "
                    "This tool is read-only and cannot execute INSERT, UPDATE, DELETE, DROP, or other DDL/DML statements."
                )

            # Additional safety: block dangerous keywords
            dangerous_keywords = ['DROP', 'DELETE', 'TRUNCATE', 'ALTER', 'CREATE', 'INSERT', 'UPDATE']
            for keyword in dangerous_keywords:
                if keyword in query_upper:
                    raise ValueError(
                        f"Query contains forbidden keyword '{keyword}'. "
                        f"Only SELECT queries are allowed for safety."
                    )

            try:
                def _execute():
                    handler = DatabaseFactory.get_database_handler(
                        db_type.lower(),
                        connection_details
                    )

                    # Execute query
                    results = handler.connection_handler.execute_query(sql_query)

                    # Limit results to prevent huge responses
                    if len(results) > 100:
                        return results[:100]

                    return results

                results = await sync_to_async(_execute)()
                return results

            except Exception as e:
                raise Exception(
                    f"Failed to execute query. "
                    f"Query: {sql_query[:100]}{'...' if len(sql_query) > 100 else ''}. "
                    f"Error: {str(e)}"
                )

        return toolset
