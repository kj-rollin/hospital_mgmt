from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class Patient(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=30)
    last_name = models.CharField(max_length=30)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(max_length=15, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['email', 'phone_number'], name='unique_patient_email_phone')
        ]

    def clean(self):
        if not self.first_name or not self.last_name:
            raise ValidationError('First and last name cannot be empty.')

    def save(self, *args, **kwargs):
        self.full_clean()  # Calls clean() and checks for constraints
        super().save(*args, **kwargs)

class Token(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return self.expires_at < timezone.now()
