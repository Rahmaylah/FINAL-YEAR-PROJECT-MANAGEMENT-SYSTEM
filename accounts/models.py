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
        ('coordinator', 'Coordinator'),
    ]
    role = models.CharField(max_length=50, choices=ROLE_CHOICES, default='student')
    middle_name = models.CharField(max_length=150, blank=True)
    registration_number = models.CharField(max_length=50, blank=True, null=True, unique=True)
    mentor = models.ForeignKey(
        'self', 
        null=True, 
        blank=True, 
        on_delete=models.SET_NULL, 
        related_name='students', 
        limit_choices_to={'role__in': ['mentor', 'coordinator']}
    )
    date_joined = models.DateTimeField(auto_now_add=True, db_column='created_at')
    updated_at = models.DateTimeField(auto_now=True, db_column='updated_at')

    # ============================================================
    # ====== FIX: Changed to ForeignKey (Single Selection) ======
    # ============================================================
    specialization = models.ForeignKey(
        'projects.ProjectType',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='specialist_mentors',
        help_text="Project type this mentor specializes in (select ONE)"
    )
    
    # ====== Mentor Bio/Description ======
    mentor_bio = models.TextField(
        blank=True,
        null=True,
        help_text="Brief description of mentor's expertise and experience"
    )
    
    # ====== Max students per mentor ======
    max_students = models.PositiveIntegerField(
        default=5,
        null=True,
        blank=True,
        help_text="Maximum number of students this mentor can handle"
    )

    def clean(self):
        super().clean()
        
        # ====== Student validations ======
        if self.role == 'student' and not self.registration_number:
            raise ValidationError({'registration_number': 'Registration number is required for students.'})
        
        # ====== Mentor is now OPTIONAL ======
        if self.role == 'student' and self.mentor:
            if self.mentor.role not in ['mentor', 'coordinator']:
                raise ValidationError({'mentor': 'Only mentors or coordinators can be assigned as mentors.'})
        
        # ====== Mentor validations ======
        if self.role == 'mentor':
            if self.max_students is not None and self.max_students < 1:
                raise ValidationError({'max_students': 'Max students must be at least 1.'})
            
            # ====== NEW: Check if mentor has reached capacity ======
            if self.pk:  # Only check for existing mentors
                current_students = User.objects.filter(mentor=self, role='student').count()
                max_slots = self.max_students or 5
                
                # If trying to reduce max_students below current students, show warning
                # This is a warning, not an error - we'll allow it but show message
                if max_slots < current_students:
                    # You can log this or add a non-field error
                    pass
    
    def save(self, *args, **kwargs):
        if self.registration_number and not self.username:
            self.username = self.registration_number
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.username} ({self.role})"
    
    # ============================================================
    # ====== HELPER METHODS ======
    # ============================================================
    
    def get_full_name(self):
        if self.first_name and self.last_name:
            if self.middle_name:
                return f"{self.first_name} {self.middle_name} {self.last_name}"
            return f"{self.first_name} {self.last_name}"
        return self.username
    
    def get_specialization_display(self):
        """Return the specialization name or 'No specialization'"""
        if self.role == 'mentor' and self.specialization:
            return self.specialization.name
        return "No specialization"
    
    def has_specialization(self, project_type):
        """Check if mentor specializes in a given project type."""
        if self.role != 'mentor':
            return False
        return self.specialization and self.specialization.id == project_type.id
    
    def get_current_students_count(self):
        """Get number of students currently assigned to this mentor"""
        if self.role != 'mentor':
            return 0
        return User.objects.filter(mentor=self, role='student').count()
    
    def get_available_student_slots(self):
        """Get number of available student slots"""
        if self.role != 'mentor':
            return 0
        
        current_students = self.get_current_students_count()
        max_slots = self.max_students or 5
        
        return max_slots - current_students
    
    def is_full(self):
        """Check if mentor has reached maximum capacity"""
        if self.role != 'mentor':
            return True
        return self.get_available_student_slots() <= 0
    
    def can_accept_students(self, count=1):
        """Check if mentor can accept more students"""
        if self.role != 'mentor':
            return False
        return self.get_available_student_slots() >= count
    
    def get_capacity_status(self):
        """Get human-readable capacity status"""
        if self.role != 'mentor':
            return 'N/A'
        available = self.get_available_student_slots()
        max_slots = self.max_students or 5
        current = self.get_current_students_count()
        
        if available <= 0:
            return f'FULL ({current}/{max_slots})'
        elif available <= 2:
            return f'{available} slot(s) remaining ({current}/{max_slots})'
        else:
            return f'{available} slots available ({current}/{max_slots})'
    
    def get_mentor_stats(self):
        """Get complete mentor statistics"""
        if self.role != 'mentor':
            return {}
        
        current_students = self.get_current_students_count()
        max_slots = self.max_students or 5
        available_slots = max_slots - current_students
        
        # Get students list with their details
        students = User.objects.filter(mentor=self, role='student').values(
            'id', 'first_name', 'middle_name', 'last_name', 
            'username', 'email', 'registration_number'
        )
        
        return {
            'current_students': current_students,
            'max_students': max_slots,
            'available_slots': available_slots,
            'is_full': available_slots <= 0,
            'specialization': self.specialization.name if self.specialization else None,
            'specialization_id': self.specialization.id if self.specialization else None,
            'capacity_status': self.get_capacity_status(),
            'students': list(students)
        }
    
    def get_students_list(self):
        """Get list of students assigned to this mentor"""
        if self.role != 'mentor':
            return []
        return User.objects.filter(mentor=self, role='student')
    
    def get_students_count_by_project_type(self):
        """Get count of students grouped by project type"""
        if self.role != 'mentor':
            return {}
        
        from django.db.models import Count, Q
        from projects.models import ProjectUser, Project
        
        # Get students assigned to this mentor
        student_ids = User.objects.filter(mentor=self, role='student').values_list('id', flat=True)
        
        # Get project types of these students through their projects
        result = {}
        
        for student_id in student_ids:
            # Get projects for this student
            projects = Project.objects.filter(
                Q(user_id=student_id) | Q(project_users__user_id=student_id)
            ).distinct()
            
            for project in projects:
                if project.project_type:
                    type_name = project.project_type.name
                    result[type_name] = result.get(type_name, 0) + 1
        
        return result