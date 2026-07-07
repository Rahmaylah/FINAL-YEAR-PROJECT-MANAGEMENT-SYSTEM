from django.contrib import admin
from .models import Project, ProjectUser, DuplicateFlag, ProjectType, ProjectDocument, Presentation, PresentationResult
from django.db.models import Q
from django.utils.html import format_html

@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')
    search_fields = ('name',)


from django.utils.safestring import mark_safe

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'year', 'status', 'duplicate_check_score', 'is_flagged_duplicate', 'created_at')
    list_filter = ('status', 'year', 'is_flagged_duplicate', 'created_at', 'project_type')
    search_fields = ('title', 'main_objective', 'specific_objectives', 'project_description')
    readonly_fields = (
        'get_title_embedding',
        'get_objectives_embedding',
        'get_combined_embedding',
        'get_objectives_display',
        'get_similar_projects'
    )

    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'title', 'project_type', 'main_objective', 'get_objectives_display', 'specific_objectives', 'project_description', 'implementation_details', 'year', 'status')
        }),
        ('Duplicate Detection', {
            'fields': ('last_similarity_check', 'is_flagged_duplicate', 'duplicate_check_score', 'get_similar_projects'),
        }),
        ('Embeddings (Read-only)', {
            'fields': ('get_title_embedding', 'get_objectives_embedding', 'get_combined_embedding'),
            'classes': ('collapse',),
        }),
    )
    
    def _format_embedding(self, embedding):
        if embedding is None:
            return 'None'
        try:
            length = len(embedding)
        except Exception:
            return str(embedding)

        if length == 0:
            return '[]'

        snippet = embedding[:5]
        return f"{length} dims; first values: {snippet}"

    def get_title_embedding(self, obj):
        return self._format_embedding(obj.title_embedding)
    get_title_embedding.short_description = 'Title Embedding'

    def get_objectives_embedding(self, obj):
        return self._format_embedding(obj.objectives_embedding)
    get_objectives_embedding.short_description = 'Objectives Embedding'

    def get_combined_embedding(self, obj):
        return self._format_embedding(obj.combined_embedding)
    get_combined_embedding.short_description = 'Combined Embedding'

    def get_objectives_display(self, obj):
        """Display specific objectives as numbered list"""
        if isinstance(obj.specific_objectives, list):
            items = ''.join(f"<li>{objective}</li>" for objective in obj.specific_objectives)
            return mark_safe(f"<ol>{items}</ol>")
        return obj.specific_objectives or "None"
    get_objectives_display.short_description = "Specific Objectives (Preview)"

    def get_similar_projects(self, obj):
        """Display similar projects by similarity score"""
        similar_flags = DuplicateFlag.objects.filter(project=obj).select_related('similar_project').order_by('-similarity_score')
        if not similar_flags:
            return "No similar projects found"
        
        html = '<table style="width:100%; border-collapse: collapse;"><tr><th style="border:1px solid #ddd; padding:8px; text-align:left;">Similar Project</th><th style="border:1px solid #ddd; padding:8px; text-align:right;">Score</th></tr>'
        for flag in similar_flags[:10]:  # Show top 10
            score_color = '#28a745' if flag.similarity_score >= 0.8 else '#ffc107' if flag.similarity_score >= 0.6 else '#dc3545'
            html += f'<tr><td style="border:1px solid #ddd; padding:8px;">{flag.similar_project.title}</td><td style="border:1px solid #ddd; padding:8px; text-align:right; color:{score_color}; font-weight:bold;">{flag.similarity_score:.3f}</td></tr>'
        html += '</table>'
        return mark_safe(html)
    get_similar_projects.short_description = "Similar Projects by Score"

@admin.register(ProjectUser)
class ProjectUserAdmin(admin.ModelAdmin):
    list_display = ('project', 'user', 'role', 'joined_at')
    list_filter = ('role', 'joined_at')
    search_fields = ('project__title', 'user__username', 'user__first_name')


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'uploaded_by', 'uploaded_at')
    list_filter = ('uploaded_at', 'project__year')
    search_fields = ('name', 'project__title', 'uploaded_by__username', 'uploaded_by__first_name')


@admin.register(Presentation)
class PresentationAdmin(admin.ModelAdmin):
    list_display = ('name', 'presentation_date', 'total_marks', 'pass_marks', 'created_at')
    list_filter = ('presentation_date', 'created_at')
    search_fields = ('name', 'description')


@admin.register(PresentationResult)
class PresentationResultAdmin(admin.ModelAdmin):
    list_display = ('presentation', 'student', 'project', 'marks', 'created_at')
    list_filter = ('presentation__presentation_date', 'marks', 'created_at')
    search_fields = ('presentation__name', 'student__username', 'student__first_name', 'student__last_name', 'project__title', 'reviewer__username', 'comment')


@admin.register(DuplicateFlag)
class DuplicateFlagAdmin(admin.ModelAdmin):
    list_display = ('project_title', 'similar_project_title', 'score_display', 'reviewed', 'created_at')
    list_filter = ('reviewed', 'created_at', 'similarity_score')
    search_fields = ('project__title', 'similar_project__title')
    readonly_fields = ('created_at', 'project', 'similar_project', 'similarity_score')
    ordering = ('-similarity_score',)

    fieldsets = (
        ('Comparison', {
            'fields': ('project', 'similar_project', 'similarity_score')
        }),
        ('Review Status', {
            'fields': ('reviewed', 'reviewed_by', 'reviewed_at')
        }),
        ('Metadata', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )

    def project_title(self, obj):
        return obj.project.title
    project_title.short_description = 'Project'

    def similar_project_title(self, obj):
        return obj.similar_project.title
    similar_project_title.short_description = 'Similar To'

    def score_display(self, obj):
        """Display similarity score with color coding"""
        if obj.similarity_score >= 0.8:
            color = '#28a745'  # Green - very similar
        elif obj.similarity_score >= 0.6:
            color = '#ffc107'  # Yellow - somewhat similar
        else:
            color = '#dc3545'  # Red - less similar
        
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            color,
            obj.similarity_score
        )
    score_display.short_description = 'Similarity Score'
