"""
URL configuration for hospital_mgmt project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# patients/urls.py
from django.urls import path
from patients.views import custom_login, dashboard, custom_logout, register, homepage, request_admin_reset, reset_password_from_token, reset_verify_username, reset_verify_email, reset_set_password, reset_with_code, set_password_from_code, register_patient, patient_receipt, patient_list, mark_attended, profile, pending_attendances

app_name = 'patients'

urlpatterns = [
    path('login/', custom_login, name='login'),
    path('', homepage, name='home'),
    path('logout/', custom_logout, name='logout'),
    path('dashboard/', dashboard, name='dashboard'),
    path('register/', register, name='register'),
    path('request-reset/' ,request_admin_reset, name='request_admin_reset'),
    path('reset-password/<str:token>/',reset_password_from_token, name='reset_password_from_token'),
    path('reset-verify-username/',reset_verify_username, name='reset_verify_username'),
    path('reset-verify-email/', reset_verify_email, name='reset_verify_email'),
    path('reset-set-password/', reset_set_password, name='reset_set_password'),
    path('reset-with-code/', reset_with_code, name='reset_with_code'),
    path('set-password-from-code/',set_password_from_code,  name='set_password_from_code'),
    path('staff/register/', register_patient, name='register_patient'),
    path('staff/receipt/', patient_receipt, name='patient_receipt'),
    path('patients/', patient_list, name='patient_list'),
    path('mark-attended/<int:patient_id>/', mark_attended, name='mark_attended'),
    path('profile/', profile, name='profile'),
    path('pending-attendances/',pending_attendances, name='pending_attendances'),
]