from django.urls import path
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

from .views import CookieTokenObtainPairView, check_auth, logout_view, refresh_token_view


from users.views import (
    UserRegistrationView,
)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user_register'),
    path('token/', CookieTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', refresh_token_view, name='token_refresh'),
    path("check-auth/", check_auth, name="check-auth"),
    path("logout/", logout_view, name="logout-view"),
]