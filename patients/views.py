# Create your views here.  
# patients/views.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth.models import User
from .models import PasswordResetRequest, Patient, Profile, Attendance
from .forms import LoginForm,RegisterForm, PatientRegistrationForm, ProfileUpdateForm
from django.utils import timezone
from datetime import timedelta, time
from django.views.decorators.http import require_POST
from django.views.decorators.cache import never_cache
from .utils import is_within_working_hours,is_within_premises

def is_customer_service(user):
    return user.groups.filter(name='Customer Service').exists() or user.is_superuser
       
def custom_login(request):
    if request.user.is_authenticated:
        return redirect('patients:dashboard')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                # --- Superuser: no restrictions, no attendance ---
                if user.is_superuser:
                    login(request, user)
                    messages.success(request, f"Welcome back, {username}!")
                    return redirect('patients:dashboard')

                # --- Non‑superuser: working hours check ---
                if not is_within_working_hours():
                    messages.error(request, "Login is only allowed during working hours (Mon-Fri, 8 AM - 6 PM).")
                    return render(request, 'patients/login.html', {'form': form})

                # --- Attendance tracking (only for non‑superusers) ---
                lat = request.POST.get('lat')
                lng = request.POST.get('lng')

                # Convert empty strings to None (so they become NULL in the database)
                if lat == '':
                    lat = None
                if lng == '':
                    lng = None

                today = timezone.now().date()
                attendance = Attendance.objects.filter(user=user, date=today).first()
                if not attendance:
                    login_time = timezone.now()
                    start_time = time(8, 0)
                    end_time = time(9, 0)
                    time_ok = start_time <= login_time.time() <= end_time

                    location_ok = False
                    if lat is not None and lng is not None:
                        try:
                            location_ok = is_within_premises(float(lat), float(lng))
                        except (ValueError, TypeError):
                            location_ok = False

                    auto_approved = time_ok and location_ok

                    Attendance.objects.create(
                        user=user,
                        login_time=login_time,
                        location_lat=lat,
                        location_lng=lng,
                        is_approved=auto_approved,
                    )
                    if auto_approved:
                        messages.success(request, f"Welcome back, {username}! Attendance auto-approved.")
                    else:
                        messages.warning(request, "Your attendance is pending supervisor approval.")
                # else: not first login – nothing to record

                # Finally, log in the user
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect('patients:dashboard')
            else:
                messages.error(request, "Invalid username or password")
        else:
            messages.error(request, "Please correct the errors below")
    else:
        form = LoginForm(request)

    return render(request, 'patients/login.html', {'form': form})
    

@login_required
def dashboard(request):
    # Determine user roles
    is_customer_service = request.user.groups.filter(name='Customer Service').exists()
    context = {
        'is_customer_service': is_customer_service,
        'user_groups': list(request.user.groups.values_list('name', flat=True)),
    }
    return render(request, 'patients/dashboard.html', context)
    
    
def custom_logout(request):
    logout(request)
    messages.info(request, "You have been logged out")
    return redirect('patients:home')
  
def register(request):
    if request.user.is_authenticated:
        return redirect('patients:dashboard')  # Already logged in

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Optionally log the user in immediately after registration
            login(request, user)
            messages.success(request, f"Account created successfully! Welcome, {user.username}.")
            return redirect('patients:dashboard')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = RegisterForm()

    return render(request, 'patients/register.html', {'form': form})
    
def homepage(request):
    if request.user.is_authenticated:
        return redirect('patients:dashboard')
    return render(request, 'patients/home.html')
    
def request_admin_reset(request):
    session_username = request.session.get('reset_username')
    show_code = False
    manual_code = None
    user_username = ''

    if session_username:
        user_username = session_username
        try:
            user = User.objects.get(username=session_username)
            # Find the most recent approved, unresolved request with a valid manual code
            reset_request = PasswordResetRequest.objects.filter(
                user=user,
                approved=True,
                is_resolved=False,
                manual_code__isnull=False,
                code_used=False
            ).order_by('-created_at').first()
            if reset_request and reset_request.is_manual_code_valid():
                show_code = True
                manual_code = reset_request.manual_code
        except User.DoesNotExist:
            # If the username doesn't exist anymore, clear session
            request.session.pop('reset_username', None)

    # ------------------------------------------------------------
    # 2. Handle POST (form submission)
    # ------------------------------------------------------------
    if request.method == 'POST':
        username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            messages.error(request, 'No account found with that username.')
            # Render the template with current context (alert may be shown if another user had code)
            return render(request, 'patients/request_admin_reset.html', {
                'show_code': show_code,
                'manual_code': manual_code,
                'user_username': user_username,
            })

        # Check 24‑hour limit
        one_day_ago = timezone.now() - timedelta(days=1)
        recent_request = PasswordResetRequest.objects.filter(
            user=user,
            created_at__gte=one_day_ago
        ).exists()

        if recent_request:
            messages.warning(
                request,
                'You have already submitted a request within the last 24 hours. '
                'Please wait before submitting another.'
            )
        else:
            # Check for pending unresolved request
            if PasswordResetRequest.objects.filter(user=user, is_resolved=False).exists():
                messages.warning(
                    request,
                    'You already have a pending request. An admin will contact you soon.'
                )
            else:
                # Create a new request
                PasswordResetRequest.objects.create(user=user)
                messages.success(
                    request,
                    'Your request has been submitted. An admin will contact you within 2 hours.'
                )
                # Store username in session so we can show alert later
                request.session['reset_username'] = username

        # Redirect to the same page (GET) to show messages and possibly the alert
        return redirect('patients:request_admin_reset')

    # ------------------------------------------------------------
    # 3. GET request – render the template with context
    # ------------------------------------------------------------
    return render(request, 'patients/request_admin_reset.html', {
        'show_code': show_code,
        'manual_code': manual_code,
        'user_username': user_username,
    })
    

User = get_user_model()


def reset_password_from_token(request, token):
    # Validate token
    try:
        reset_request = PasswordResetRequest.objects.get(reset_token=token)
    except PasswordResetRequest.DoesNotExist:
        messages.error(request, 'Invalid or expired reset link.')
        return redirect('patients:login')

    if not reset_request.is_token_valid():
        messages.error(request, 'This reset link has expired. Please request a new one.')
        return redirect('patients:request_admin_reset')

    # Store token in session for the subsequent steps
    request.session['reset_token'] = token

    # First step: ask for username
    return redirect('patients:reset_verify_username')
    

def reset_verify_username(request):
    token = request.session.get('reset_token')
    if not token:
        messages.error(request, 'Session expired. Please start over.')
        return redirect('patients:login')

    try:
        reset_request = PasswordResetRequest.objects.get(reset_token=token)
    except PasswordResetRequest.DoesNotExist:
        messages.error(request, 'Invalid reset link.')
        return redirect('patients:login')

    if request.method == 'POST':
        entered_username = request.POST.get('username')
        if entered_username == reset_request.user.username:
            # Save that username is verified
            request.session['username_verified'] = True
            return redirect('patients:reset_verify_email')
        else:
            messages.error(request, 'Username does not match the account that requested the reset.')
    return render(request, 'patients/reset_verify_username.html')
    

def reset_verify_email(request):
    token = request.session.get('reset_token')
    username_verified = request.session.get('username_verified')
    if not token or not username_verified:
        messages.error(request, 'Session expired or verification missing. Please start over.')
        return redirect('patients:login')

    try:
        reset_request = PasswordResetRequest.objects.get(reset_token=token)
    except PasswordResetRequest.DoesNotExist:
        messages.error(request, 'Invalid reset link.')
        return redirect('patients:login')

    if request.method == 'POST':
        entered_email = request.POST.get('email')
        if entered_email == reset_request.user.email:
            # All verifications passed
            request.session['reset_allowed'] = True
            return redirect('patients:reset_set_password')
        else:
            messages.error(request, 'Email does not match the account that requested the reset.')
    return render(request, 'patients/reset_verify_email.html')
    

def reset_set_password(request):
    token = request.session.get('reset_token')
    reset_allowed = request.session.get('reset_allowed')
    if not token or not reset_allowed:
        messages.error(request, 'Session expired or unauthorized. Please start over.')
        return redirect('patients:login')

    try:
        reset_request = PasswordResetRequest.objects.get(reset_token=token)
    except PasswordResetRequest.DoesNotExist:
        messages.error(request, 'Invalid reset link.')
        return redirect('patients:login')

    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 and password1 == password2:
            user = reset_request.user
            user.set_password(password1)
            user.save()
            # Mark request as resolved
            reset_request.is_resolved = True
            reset_request.resolved_at = timezone.now()
            reset_request.reset_token = None  # Invalidate token
            reset_request.save()
            # Clear session data
            for key in ['reset_token', 'username_verified', 'reset_allowed']:
                request.session.pop(key, None)
            messages.success(request, 'Your password has been reset. Please log in with your new password.')
            return redirect('patients:login')
        else:
            messages.error(request, 'Passwords do not match or are empty.')

    return render(request, 'patients/reset_set_password.html')
    
def reset_with_code(request):
    """User enters the manual code provided by admin."""
    if request.method == 'POST':
        code = request.POST.get('code')
        try:
            reset_request = PasswordResetRequest.objects.get(manual_code=code, code_used=False)
        except PasswordResetRequest.DoesNotExist:
            messages.error(request, 'Invalid or expired code.')
            return render(request, 'patients/reset_with_code.html')

        if not reset_request.is_manual_code_valid():
            messages.error(request, 'This code has expired. Please request a new one.')
            return render(request, 'patients/reset_with_code.html')

        # Code is valid – store in session and redirect to password set form
        request.session['reset_code'] = code
        return redirect('patients:set_password_from_code')

    return render(request, 'patients/reset_with_code.html')

def set_password_from_code(request):
    """Form to set a new password after code verification."""
    code = request.session.get('reset_code')
    if not code:
        messages.error(request, 'Session expired or invalid code.')
        return redirect('patients:login')

    try:
        reset_request = PasswordResetRequest.objects.get(manual_code=code, code_used=False)
    except PasswordResetRequest.DoesNotExist:
        messages.error(request, 'Invalid code.')
        return redirect('patients:login')

    if not reset_request.is_manual_code_valid():
        messages.error(request, 'Code expired.')
        return redirect('patients:login')

    if request.method == 'POST':
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        if password1 and password1 == password2:
            user = reset_request.user
            user.set_password(password1)
            user.save()
            # Mark the code as used and the request as resolved
            reset_request.code_used = True
            reset_request.is_resolved = True
            reset_request.resolved_at = timezone.now()
            reset_request.save()
            # Clear session
            request.session.pop('reset_code', None)
            messages.success(request, 'Password reset successful. Please log in with your new password.')
            return redirect('patients:login')
        else:
            messages.error(request, 'Passwords do not match or are empty.')

    return render(request, 'patients/set_password_from_code.html')
    
    
def register_patient(request):
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            patient = form.save()
            request.session['last_registered_patient_id'] = patient.patient_id
            return redirect('patients:patient_receipt')
        else:
            messages.error(request, 'Please correct the errors below.')
            # Return the form with errors
            return render(request, 'patients/register_patient.html', {'form': form})
    else:
        form = PatientRegistrationForm()
    return render(request, 'patients/register_patient.html', {'form': form})	
			
	
@login_required
@user_passes_test(is_customer_service, login_url='patients:login')

def patient_receipt(request):
    patient_id = request.session.get('last_registered_patient_id')
    if not patient_id:
        messages.error(request, 'No recent registration found.')
        return redirect('patients:register_patient')
    try:
        patient = Patient.objects.get(patient_id=patient_id)
    except Patient.DoesNotExist:
        messages.error(request, 'Patient record not found.')
        return redirect('patients:register_patient')
    # Clear session to avoid reuse
    del request.session['last_registered_patient_id']
    return render(request, 'patients/receipt.html', {'patient': patient, 'served_by': request.user})
    
@login_required
def patient_list(request):
    # Allow doctors and admins; customer service should not see this page
    is_customer_service = request.user.groups.filter(name='Customer Service').exists()
    if is_customer_service and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to view this page.')
        return redirect('patients:dashboard')

    # Get all patients, ordered by creation date (most recent first)
    patients = Patient.objects.all().order_by('-created_at')
    return render(request, 'patients/patient_list.html', {'patients': patients})
    
@login_required
def mark_attended(request, patient_id):
    # Only doctors/admins can mark attended
    is_customer_service = request.user.groups.filter(name='Customer Service').exists()
    if is_customer_service and not request.user.is_superuser:
        messages.error(request, 'You do not have permission to perform this action.')
        return redirect('patients:dashboard')

    patient = get_object_or_404(Patient, id=patient_id)
    patient.attended = True
    patient.save()
    messages.success(request, f'Patient {patient.first_name} {patient.last_name} marked as attended.')
    return redirect('patients:patient_list')
    
    
@login_required
def profile(request):
    # Ensure the user has a profile
    if not hasattr(request.user, 'profile'):
        Profile.objects.create(user=request.user)

    if request.method == 'POST':
        form = ProfilePictureForm(request.POST, request.FILES, instance=request.user.profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile picture updated!')
            return redirect('patients:profile')
    else:
        form = ProfileUpdateForm(instance=request.user.profile)

    context = {
        'form': form,
        'user': request.user,
    }
    return render(request, 'patients/profile.html', context)    
    
def is_supervisor(user):
    return user.groups.filter(name='Supervisor').exists() or user.is_superuser

@login_required
@user_passes_test(is_supervisor)
def pending_attendances(request):
    today = timezone.now().date()
    pending = Attendance.objects.filter(is_approved=False, date=today).order_by('login_time')

    if request.method == 'POST':
        attendance_id = request.POST.get('attendance_id')
        action = request.POST.get('action')
        if action == 'approve' and attendance_id:
            try:
                attendance = Attendance.objects.get(id=attendance_id)
                if not attendance.is_approved:  # prevent double approval
                    attendance.is_approved = True
                    attendance.approved_by = request.user
                    attendance.approved_at = timezone.now()
                    attendance.save()
                    messages.success(request, f'Attendance for {attendance.user.username} approved.')
            except Attendance.DoesNotExist:
                messages.error(request, 'Attendance record not found.')
        elif action == 'reject' and attendance_id:
            try:
                attendance = Attendance.objects.get(id=attendance_id)
                attendance.delete()
                messages.warning(request, f'Attendance for {attendance.user.username} rejected and removed.')
            except Attendance.DoesNotExist:
                messages.error(request, 'Attendance record not found.')
        return redirect('patients:pending_attendances')  # stays on same page to see updated list

    return render(request, 'patients/pending_attendances.html', {'attendances': pending})
    