# Create your models here.
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid
import secrets
import random
import string
from datetime import timedelta, datetime


class Patient(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    ]

    # Personal details
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True, null=True)   # added for surname
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    phone = models.CharField(max_length=15)
    address = models.TextField()               # can be used for place of residence
    # Unique identifier
    patient_id = models.CharField(max_length=50, unique=True, blank=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    attended = models.BooleanField(default=False)   # new field

    def save(self, *args, **kwargs):
        if not self.patient_id:
            self.patient_id = self.generate_patient_id()
        super().save(*args, **kwargs)

    def generate_patient_id(self):
        # Format: PATIENT/YYMMDDHHMMSS/RANDOM/HSP
        now = datetime.now()
        timestamp = now.strftime('%y%m%d%H%M%S')
        rand = secrets.randbelow(900) + 100
        return f"PATIENT/{timestamp}/{rand}/HSP"

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.patient_id}"


class PasswordResetRequest(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_requests')
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=False)
    reset_token = models.CharField(max_length=100, blank=True, null=True, unique=True)
    token_created_at = models.DateTimeField(null=True, blank=True)
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    admin_notes = models.TextField(blank=True)

    # Manual code fields
    manual_code = models.CharField(max_length=10, blank=True, null=True, unique=True)
    code_created_at = models.DateTimeField(blank=True, null=True)
    code_used = models.BooleanField(default=False)

    def generate_token(self):
        self.reset_token = uuid.uuid4().hex
        self.token_created_at = timezone.now()
        self.save()

    def is_token_valid(self):
        if not self.reset_token or not self.token_created_at:
            return False
        expiry = self.token_created_at + timedelta(hours=1)
        return timezone.now() < expiry

    def generate_manual_code(self):
        """Generate a 6‑digit numeric code and set creation time."""
        self.manual_code = ''.join(random.choices(string.digits, k=6))
        self.code_created_at = timezone.now()
        self.code_used = False
        self.save()
        return self.manual_code

    def is_manual_code_valid(self):
        """Check if code exists, is unused, and not expired (1 hour)."""
        if not self.manual_code or not self.code_created_at or self.code_used:
            return False
        expiry = self.code_created_at + timedelta(hours=1)
        return timezone.now() < expiry

    def __str__(self):
        return f"{self.user.username} - {self.created_at}"

    class Meta:
        ordering = ['-created_at']

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(max_length=500, blank=True)
    profile_picture = models.ImageField(upload_to='profile_pics/', blank=True, null=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"
        
class Attendance(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField(auto_now_add=True)
    login_time = models.DateTimeField(auto_now_add=True)
    location_lat = models.FloatField(null=True, blank=True)
    location_lng = models.FloatField(null=True, blank=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_attendances')
    approved_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.date} - {'Approved' if self.is_approved else 'Pending'}"
        