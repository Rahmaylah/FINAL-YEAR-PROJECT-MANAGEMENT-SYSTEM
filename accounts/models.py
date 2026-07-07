from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator

class User(AbstractUser):
    # Override username field with custom validator that allows slash (/)
    username = models.CharField(
        max_length=150,
        unique=True,
        validators=[
            RegexValidator(
                regex=r'^[\w.@+/-]+$',  # Added slash (/) to allowed characters
                message='Enter a valid username. This value may contain only letters, numbers, and @/./+/-/_ characters.',
                code='invalid'
            )
        ],
        error_messages={
            'unique': "A user with that username already exists.",
        },
        help_text='Required. 150 characters or fewer. Letters, numbers and @/./+/-/_ characters only.'
    )
    
    ROLE_CHOICES = [
        ('student', 'Student'),
        ('mentor', 'Mentor'),
        ('coordinator', 'Coordinator'),  # Manages mentors, higher permissions than mentors
    ]
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='student')
    middle_name = models.CharField(max_length=150, blank=True)  # Added for three-name structure
    registration_number = models.CharField(max_length=50, blank=True, null=True, unique=True)  # Only for students
    mentor = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='students', limit_choices_to={'role__in': ['mentor', 'coordinator']})
    date_joined = models.DateTimeField(auto_now_add=True, db_column='created_at')  # Map to schema's created_at
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')  # Map to schema's updated_at

    def clean(self):
        super().clean()
        if self.role == 'student' and not self.registration_number:
            raise ValidationError({'registration_number': 'Registration number is required for students.'})
        if self.role == 'student' and not self.mentor:
            raise ValidationError({'mentor': 'Every student must have a mentor.'})
    
    def save(self, *args, **kwargs):
        # Auto-set username from registration_number if username is empty
        if self.registration_number and not self.username:
            self.username = self.registration_number
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"