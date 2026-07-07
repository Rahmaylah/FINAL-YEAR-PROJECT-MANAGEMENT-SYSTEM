from django.contrib import admin
from .models import SystemSettings


@admin.register(SystemSettings)
class SystemSettingsAdmin(admin.ModelAdmin):
    list_display = (
        'duplicate_algorithm',
        'duplicate_search_years_back',
        'duplicate_similarity_threshold',
        'duplicate_auto_flag_threshold',
        'updated_at',
    )

    def has_add_permission(self, request):
        return not SystemSettings.objects.exists()
