from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User

class CustomUserAdmin(UserAdmin):
    # Display custom fields in the list view
    list_display = ('username', 'email', 'first_name', 'middle_name', 'last_name', 'role', 'registration_number', 'mentor', 'is_active', 'date_joined')
    list_filter = ('role', 'is_active', 'is_staff', 'date_joined')
    search_fields = ('username', 'first_name', 'middle_name', 'last_name', 'email', 'registration_number')

    # Make date_joined read-only since it's auto_now_add
    readonly_fields = ('date_joined',)

    # Organize fields into sections
    fieldsets = UserAdmin.fieldsets + (
        ('Additional Information', {
            'fields': ('middle_name', 'role', 'registration_number', 'mentor'),
        }),
    )

    # Add fields for user creation/editing
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Additional Information', {
            'fields': ('first_name', 'middle_name', 'last_name', 'role', 'registration_number', 'mentor'),
        }),
    )

# Register the custom User admin
admin.site.register(User, CustomUserAdmin)
