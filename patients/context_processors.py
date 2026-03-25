from django.utils import timezone
from .models import Attendance

def attendance_notifications(request):
    context = {}
    if request.user.is_authenticated:
        is_supervisor = request.user.groups.filter(name='Supervisor').exists() or request.user.is_superuser
        context['is_supervisor'] = is_supervisor

        today = timezone.now().date()
        # Bell count: today's pending attendances (only for supervisors)
        if is_supervisor:
            context['pending_attendance_count'] = Attendance.objects.filter(
                is_approved=False, date=today
            ).count()
        else:
            context['pending_attendance_count'] = 0

        # Employee warning: does this user have any unapproved attendance?
        context['user_has_unapproved_attendance'] = Attendance.objects.filter(
            user=request.user, is_approved=False
        ).exists()
    else:
        context['is_supervisor'] = False
        context['pending_attendance_count'] = 0
        context['user_has_unapproved_attendance'] = False

    return context