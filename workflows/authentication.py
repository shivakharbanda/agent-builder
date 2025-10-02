from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.utils import timezone


class SessionIDAuthentication(BaseAuthentication):
    """
    Authenticate using session_id from WorkflowBuilderSession.

    This authentication backend is specifically designed for AI agent tool calls
    from the FastAPI workflow builder service. It allows stateless FastAPI to
    authenticate requests by passing session_id, which maps to a Django user.

    Authentication flow:
    1. Check for 'session_id' in query params (GET requests)
    2. Check for 'session_id' in request body (POST requests)
    3. Look up WorkflowBuilderSession in database
    4. Validate session is active and not expired
    5. Return user from session

    If no session_id is present, returns None to allow other authentication
    backends to handle the request (JWT, Session, etc.)
    """

    def authenticate(self, request):
        from workflows.models import WorkflowBuilderSession

        # Try to get session_id from query params first (GET requests)
        session_id = request.query_params.get('session_id')

        # If not in query params, try request body (POST requests)
        if not session_id and hasattr(request, 'data') and isinstance(request.data, dict):
            session_id = request.data.get('session_id')

        # If no session_id, let other auth backends handle it
        if not session_id:
            return None

        try:
            # Look up session with user relationship
            session = WorkflowBuilderSession.objects.select_related('created_by').get(
                session_id=session_id,
                is_active=True
            )

            # Check if session has expired
            if session.expires_at < timezone.now():
                raise AuthenticationFailed(
                    f'Session {session_id} has expired at {session.expires_at.isoformat()}'
                )

            # Return user and None for auth (we don't use token-based auth here)
            return (session.created_by, None)

        except WorkflowBuilderSession.DoesNotExist:
            raise AuthenticationFailed(
                f'Invalid or inactive session_id: {session_id}'
            )

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the WWW-Authenticate
        header in a 401 Unauthenticated response.
        """
        return 'SessionID realm="api"'
