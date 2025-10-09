"""
Schedule Trigger Node Handler

Handles scheduled workflow triggers - workflows that run on a cron schedule.
"""

import re
from datetime import datetime
from typing import Any, Dict
from workflows.execution.node_handlers.trigger_base import BaseTriggerNode


class ScheduleTriggerNode(BaseTriggerNode):
    """
    Schedule trigger node implementation.

    This trigger type allows workflows to be started on a recurring schedule
    using cron expressions (e.g., daily, hourly, weekly).

    Configuration Fields:
        schedule (str, required): Cron expression (e.g., "0 9 * * *" for daily at 9am)
        timezone (str, optional): Timezone for schedule (default: UTC)
        enabled (bool, optional): Whether schedule is enabled (default: True)

    Output:
        Returns execution metadata including scheduled time, actual time, etc.

    Note:
        Actual scheduling is handled by a separate scheduler service (Celery, etc.).
        This node just validates the schedule configuration and provides execution metadata.
    """

    node_type: str = 'trigger_schedule'

    def validate(self) -> bool:
        """
        Validate schedule trigger configuration.

        Checks:
        - Base trigger validation
        - schedule field is present and valid cron expression
        - timezone is valid (if provided)
        - enabled is boolean (if provided)

        Returns:
            bool: True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Call parent validation
        super().validate()

        # Check required fields
        if 'schedule' not in self.configuration:
            raise ValueError("schedule field is required for schedule trigger")

        schedule = self.configuration['schedule']
        if not isinstance(schedule, str) or not schedule.strip():
            raise ValueError("schedule must be a non-empty string")

        # Validate cron expression format
        # Basic validation: 5 fields separated by spaces
        # Format: minute hour day month weekday
        cron_parts = schedule.strip().split()
        if len(cron_parts) != 5:
            raise ValueError(
                "schedule must be a valid cron expression with 5 fields: "
                "minute hour day month weekday (e.g., '0 9 * * *')"
            )

        # Validate each cron field
        self._validate_cron_field(cron_parts[0], 0, 59, "minute")
        self._validate_cron_field(cron_parts[1], 0, 23, "hour")
        self._validate_cron_field(cron_parts[2], 1, 31, "day")
        self._validate_cron_field(cron_parts[3], 1, 12, "month")
        self._validate_cron_field(cron_parts[4], 0, 6, "weekday")

        # Validate timezone (if provided)
        if 'timezone' in self.configuration:
            timezone = self.configuration['timezone']
            if not isinstance(timezone, str):
                raise ValueError("timezone must be a string")
            # Basic timezone validation - just check it's not empty
            if not timezone.strip():
                raise ValueError("timezone cannot be empty")

        # Validate enabled (if provided)
        if 'enabled' in self.configuration:
            enabled = self.configuration['enabled']
            if not isinstance(enabled, bool):
                raise ValueError("enabled must be a boolean")

        return True

    def _validate_cron_field(self, field: str, min_val: int, max_val: int, field_name: str):
        """
        Validate a single cron field.

        Args:
            field: Cron field value (e.g., "*/5", "1-10", "3", "*")
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            field_name: Name of field for error messages

        Raises:
            ValueError: If field is invalid
        """
        # Allow wildcards
        if field == '*':
            return

        # Allow step values (*/5, 1-10/2, etc.)
        if '/' in field:
            parts = field.split('/')
            if len(parts) != 2:
                raise ValueError(f"Invalid {field_name} field: {field}")
            # Validate step is a number
            try:
                step = int(parts[1])
                if step <= 0:
                    raise ValueError(f"Step value must be positive in {field_name}: {field}")
            except ValueError:
                raise ValueError(f"Invalid step value in {field_name}: {field}")
            # Validate range part (before /)
            if parts[0] != '*':
                self._validate_cron_field(parts[0], min_val, max_val, field_name)
            return

        # Allow ranges (1-10)
        if '-' in field:
            parts = field.split('-')
            if len(parts) != 2:
                raise ValueError(f"Invalid range in {field_name}: {field}")
            try:
                start = int(parts[0])
                end = int(parts[1])
                if start < min_val or start > max_val or end < min_val or end > max_val:
                    raise ValueError(f"{field_name} values must be between {min_val} and {max_val}: {field}")
                if start > end:
                    raise ValueError(f"Invalid range in {field_name} (start > end): {field}")
            except ValueError as e:
                raise ValueError(f"Invalid range in {field_name}: {field}")
            return

        # Allow lists (1,5,10)
        if ',' in field:
            for value in field.split(','):
                self._validate_cron_field(value.strip(), min_val, max_val, field_name)
            return

        # Must be a single number
        try:
            num = int(field)
            if num < min_val or num > max_val:
                raise ValueError(f"{field_name} must be between {min_val} and {max_val}: {field}")
        except ValueError:
            raise ValueError(f"Invalid {field_name} value: {field}")

    def execute(self, input_data: Any = None) -> Dict[str, Any]:
        """
        Execute schedule trigger node.

        Returns execution metadata including schedule information.

        Args:
            input_data: Ignored (trigger nodes don't receive input)

        Returns:
            dict: Execution metadata with schedule information
        """
        now = datetime.now()

        # Build execution data
        execution_data = {
            '_trigger': {
                'type': 'schedule',
                'node_id': self.node_id,
                'workflow_id': self.workflow_id,
                'execution_id': self.execution_id,
                'schedule': self.configuration['schedule'],
                'timezone': self.configuration.get('timezone', 'UTC'),
                'enabled': self.configuration.get('enabled', True),
                'executed_at': now.isoformat(),
                'description': self.configuration.get('description', f"Scheduled trigger: {self.configuration['schedule']}")
            }
        }

        return execution_data

    def get_trigger_metadata(self) -> Dict[str, Any]:
        """Get schedule trigger metadata."""
        return {
            **super().get_trigger_metadata(),
            'schedule': self.configuration.get('schedule'),
            'timezone': self.configuration.get('timezone', 'UTC'),
            'enabled': self.configuration.get('enabled', True),
            'description': self.configuration.get('description', f"Scheduled: {self.configuration.get('schedule')}")
        }
