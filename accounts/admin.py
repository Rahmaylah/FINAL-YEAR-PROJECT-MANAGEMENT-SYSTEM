from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from .models import User
from projects.models import ProjectType


class CustomUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = UserCreationForm.Meta.fields + (
            'first_name', 'middle_name', 'last_name', 
            'email', 'role', 'registration_number', 'mentor',
            'specialization', 'mentor_bio', 'max_students'
        )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if 'mentor' in self.fields:
            self.fields['mentor'].required = False
            self.fields['mentor'].empty_label = "No mentor assigned"
            self.fields['mentor'].help_text = "Optional - select a mentor or leave empty"
        
        # ====== Single Select - ONE project type only ======
        if 'specialization' in self.fields:
            project_types = ProjectType.objects.all().order_by('name')
            choices = [('', '---------')] + [(pt.id, pt.name) for pt in project_types]
            
            if not project_types.exists():
                self.fields['specialization'].widget = forms.Select(attrs={
                    'disabled': 'disabled',
                    'style': 'color: #999;'
                })
                self.fields['specialization'].help_text = "No project types available. Please add project types first."
            else:
                self.fields['specialization'].widget = forms.Select(choices=choices, attrs={
                    'style': 'width: 100%;'
                })
                self.fields['specialization'].required = False
                self.fields['specialization'].help_text = "Select ONE project type this mentor specializes in"
                self.fields['specialization'].choices = choices
        
        if 'mentor_bio' in self.fields:
            self.fields['mentor_bio'].required = False
            self.fields['mentor_bio'].widget = forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Brief description of mentor\'s expertise...'
            })
            self.fields['mentor_bio'].help_text = "Brief description of mentor's expertise (optional)"
        
        if 'max_students' in self.fields:
            self.fields['max_students'].required = False
            self.fields['max_students'].initial = 5
            self.fields['max_students'].help_text = "Maximum number of students this mentor can handle (default: 5)"


class CustomUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        if 'mentor' in self.fields:
            self.fields['mentor'].required = False
            self.fields['mentor'].empty_label = "No mentor assigned"
            self.fields['mentor'].help_text = "Optional - select a mentor or leave empty"
        
        # ====== Single Select - ONE project type only ======
        if 'specialization' in self.fields:
            project_types = ProjectType.objects.all().order_by('name')
            choices = [('', '---------')] + [(pt.id, pt.name) for pt in project_types]
            
            if not project_types.exists():
                self.fields['specialization'].widget = forms.Select(attrs={
                    'disabled': 'disabled',
                    'style': 'color: #999;'
                })
                self.fields['specialization'].help_text = "No project types available. Please add project types first."
            else:
                self.fields['specialization'].widget = forms.Select(choices=choices, attrs={
                    'style': 'width: 100%;'
                })
                self.fields['specialization'].required = False
                self.fields['specialization'].help_text = "Select ONE project type this mentor specializes in"
                self.fields['specialization'].choices = choices
        
        if 'mentor_bio' in self.fields:
            self.fields['mentor_bio'].required = False
            self.fields['mentor_bio'].widget = forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Brief description of mentor\'s expertise...'
            })
            self.fields['mentor_bio'].help_text = "Brief description of mentor's expertise (optional)"
        
        if 'max_students' in self.fields:
            self.fields['max_students'].required = False
            self.fields['max_students'].initial = 5
            self.fields['max_students'].help_text = "Maximum number of students this mentor can handle (default: 5)"


class CustomUserAdmin(UserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm

    list_display = (
        'username', 'email', 'first_name', 'middle_name', 'last_name', 
        'role', 'registration_number', 'mentor', 'get_specialization', 
        'get_current_students', 'get_capacity_status', 'is_active', 'date_joined'
    )
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = (
        'username', 'first_name', 'middle_name', 'last_name', 
        'email', 'registration_number', 'mentor_bio'
    )
    readonly_fields = ('date_joined',)

    def get_specialization(self, obj):
        if obj.role == 'mentor' and obj.specialization:
            return obj.specialization.name
        return "-"
    get_specialization.short_description = "Specialization"

    def get_current_students(self, obj):
        if obj.role == 'mentor':
            count = User.objects.filter(mentor=obj, role='student').count()
            return count
        return "-"
    get_current_students.short_description = "Current Students"

    def get_capacity_status(self, obj):
        if obj.role == 'mentor':
            max_students = obj.max_students or 5
            current = User.objects.filter(mentor=obj, role='student').count()
            available = max_students - current
            if available <= 0:
                return "FULL"
            elif available <= 2:
                return f"{available} slots left"
            else:
                return f"{available} slots available"
        return "-"
    get_capacity_status.short_description = "Capacity Status"

    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'middle_name', 'last_name', 'email')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Additional Information', {
            'fields': ('role', 'registration_number', 'mentor'),
        }),
        ('Mentor Information', {
            'fields': ('specialization', 'mentor_bio', 'max_students'),
            'classes': ('collapse',),
            'description': 'Set mentor specialization, capacity, and bio'
        }),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'username', 'password1', 'password2', 
                'first_name', 'middle_name', 'last_name', 'email', 
                'role', 'registration_number', 'mentor',
                'specialization', 'mentor_bio', 'max_students'
            ),
        }),
    )


admin.site.register(User, CustomUserAdmin)