from django.shortcuts import redirect
from django.contrib import messages
from django.urls import reverse
from django.utils.deprecation import MiddlewareMixin
from .utils import is_within_working_hours

class WorkingHoursMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Allow admin (superuser) always
        if request.user.is_authenticated and request.user.is_superuser:
            return None

        # Exclude certain URLs (login, logout, static files, etc.)
        excluded_paths = [
            reverse('patients:login'),
            reverse('patients:logout'),
            '/admin/',                # Django admin
            '/static/',
            '/media/',
        ]
        if any(request.path.startswith(path) for path in excluded_paths):
            return None

        # If user is authenticated but not superuser
        if request.user.is_authenticated:
            if not is_within_working_hours():
                # Logout the user
                from django.contrib.auth import logout
                logout(request)
                messages.error(request, "Access is only allowed during working hours (Mon-Fri, 8 AM - 6 PM).")
                return redirect('patients:login')
        return None