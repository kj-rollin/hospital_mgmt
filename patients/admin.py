# Register your models here.
from django.contrib import admin, messages
from .models import Patient, PasswordResetRequest
from django.shortcuts import redirect
from django.urls import reverse
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
# patients/admin.py
from django.contrib.auth.models import Group, User


admin.site.register(Patient)     

@admin.register(PasswordResetRequest)
class PasswordResetRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'created_at', 'approved', 'is_resolved', 'manual_code', 'code_used', 'code_expiry')
    list_filter = ('approved', 'is_resolved', 'created_at', 'code_used')
    search_fields = ('user__username', 'user__email', 'manual_code')
    actions = ['approve_requests', 'generate_manual_codes', 'mark_resolved']

    def code_expiry(self, obj):
        """Show when the manual code expires."""
        if obj.manual_code and obj.code_created_at:
            expiry = obj.code_created_at + timezone.timedelta(hours=1)
            if timezone.now() > expiry:
                return "Expired"
            else:
                return expiry.strftime("%Y-%m-%d %H:%M")
        return "-"
    code_expiry.short_description = "Code Expiry"

    def approve_requests(self, request, queryset):
        for reset_request in queryset:
            if not reset_request.approved and not reset_request.is_resolved:
                # Generate email token
                reset_request.generate_token()
                # Generate manual code
                reset_request.generate_manual_code()
                reset_request.approved = True
                reset_request.save()

                # Send email with the reset link
                reset_link = request.build_absolute_uri(
                    reverse('patients:reset_password_from_token', args=[reset_request.reset_token])
                )
                subject = 'Password Reset Request Approved'
                message = render_to_string('patients/admin_approved_reset_email.html', {
                    'user': reset_request.user,
                    'reset_link': reset_link,
                })
                send_mail(subject, message, 'noreply@yourhospital.com', [reset_request.user.email])

                messages.success(request, 
                    f"Approved {reset_request.user.username}. Email sent and manual code generated: {reset_request.manual_code}")
        self.message_user(request, f'Approved {queryset.count()} request(s).')
    approve_requests.short_description = "Approve requests (send email + generate manual code)"

    def generate_manual_codes(self, request, queryset):
        """Manually generate/regenerate a manual code for selected requests."""
        for reset_request in queryset:
            if not reset_request.approved:
                self.message_user(request, f"{reset_request.user} not approved yet. Cannot generate code.")
                continue
            if reset_request.is_resolved:
                self.message_user(request, f"{reset_request.user} already resolved.")
                continue
            # Generate a new manual code
            code = reset_request.generate_manual_code()
            messages.success(request, f"Generated new code {code} for {reset_request.user.username}")
        self.message_user(request, f"Generated manual codes for {queryset.count()} request(s).")
    generate_manual_codes.short_description = "Generate/Regenerate manual codes"

    def mark_resolved(self, request, queryset):
        updated = queryset.update(is_resolved=True, resolved_at=timezone.now())
        self.message_user(request, f'{updated} request(s) marked as resolved.', messages.SUCCESS)
    mark_resolved.short_description = "Mark selected requests as resolved"
    


# Inline for the many‑to‑many relationship between User and Group
class UserGroupInline(admin.TabularInline):
    model = User.groups.through   # intermediate model
    extra = 1
    verbose_name = "User"
    verbose_name_plural = "Users in this group"

# Unregister the default Group admin
admin.site.unregister(Group)

# Register Group with the custom inline
@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    inlines = [UserGroupInline]
    list_display = ('name', 'user_count')

    def user_count(self, obj):
        return obj.user_set.count()
    user_count.short_description = 'Number of users'