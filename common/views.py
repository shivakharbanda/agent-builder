from django.http import JsonResponse
from django.views.decorators.http import require_GET

@require_GET
def health_check(request):
    """Simple health check endpoint"""
    return JsonResponse({
        'status': 'healthy',
        'message': 'Agent Builder API is running'
    })
