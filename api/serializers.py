from rest_framework import serializers
from accounts.models import User
from projects.models import Project, ProjectType, ProjectUser, DuplicateFlag, ProjectDocument, Presentation, PresentationResult
from projects.models import PresentationCriteria, PresentationResultCriteria
from core.models import SystemSettings


class StudentMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'middle_name', 'last_name', 'email', 'role', 'registration_number']


class MentorMiniSerializer(serializers.ModelSerializer):
    students = serializers.SerializerMethodField()

    def get_students(self, obj):
        if obj.role in ['mentor', 'coordinator']:
            students = obj.students.filter(role='student')
            return StudentMiniSerializer(students, many=True).data
        return []

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'middle_name', 'last_name', 'email', 'role', 'students']


class UserSerializer(serializers.ModelSerializer):
    mentor_info = serializers.SerializerMethodField()
    students = serializers.SerializerMethodField()

    def get_mentor_info(self, obj):
        if obj.mentor:
            return MentorMiniSerializer(obj.mentor).data
        return None

    def get_students(self, obj):
        if obj.role in ['mentor', 'coordinator']:
            students = obj.students.filter(role='student')
            return MentorMiniSerializer(students, many=True).data
        return []

    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'middle_name', 'last_name', 'email', 'role', 'registration_number', 'mentor', 'mentor_info', 'students', 'is_active', 'date_joined']


class ProjectTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectType
        fields = ['id', 'name', 'description']


class ProjectDocumentSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.SerializerMethodField()

    class Meta:
        model = ProjectDocument
        fields = ['id', 'project', 'name', 'description', 'file', 'uploaded_by', 'uploaded_by_name', 'uploaded_at']
        read_only_fields = ['project', 'uploaded_by', 'uploaded_at']

    def get_uploaded_by_name(self, obj):
        if obj.uploaded_by:
            return f"{obj.uploaded_by.first_name} {obj.uploaded_by.middle_name} {obj.uploaded_by.last_name}".strip()
        return None


# ============================================================
# ====== FIXED: PresentationResultSerializer - WITH CRITERIA SCORES ======
# ============================================================

class PresentationResultSerializer(serializers.ModelSerializer):
    presentation_name = serializers.CharField(source='presentation.name', read_only=True)
    presentation_date = serializers.DateField(source='presentation.presentation_date', read_only=True)
    presentation_total_marks = serializers.FloatField(source='presentation.total_marks', read_only=True)
    presentation_pass_marks = serializers.FloatField(source='presentation.pass_marks', read_only=True)
    student_name = serializers.SerializerMethodField()
    project_title = serializers.CharField(source='project.title', read_only=True)
    reviewer_name = serializers.SerializerMethodField()
    
    # Criteria scores
    criteria_scores = serializers.SerializerMethodField()
    
    class Meta:
        model = PresentationResult
        fields = [
            'id', 'presentation', 'presentation_name', 'presentation_date', 
            'presentation_total_marks', 'presentation_pass_marks', 
            'student', 'student_name', 'project', 'project_title', 
            'reviewer', 'reviewer_name', 'comment', 'marks', 
            'criteria_total', 'is_graded_by_criteria',
            'criteria_scores',
            'created_at', 'updated_at'
        ]
        read_only_fields = [
            'presentation_name', 'presentation_date', 'presentation_total_marks', 
            'presentation_pass_marks', 'student_name', 'project_title', 
            'reviewer_name', 'created_at', 'updated_at',
            'criteria_scores', 'criteria_total'
        ]

    def get_student_name(self, obj):
        if obj.student:
            return f"{obj.student.first_name} {obj.student.middle_name} {obj.student.last_name} {obj.student.registration_number}".strip()
        return None

    def get_reviewer_name(self, obj):
        if obj.reviewer:
            return f"{obj.reviewer.first_name} {obj.reviewer.middle_name} {obj.reviewer.last_name}".strip()
        return None
    
    def get_criteria_scores(self, obj):
        """Get criteria scores for this presentation result"""
        try:
            scores = obj.criteria_scores.all()
            if scores.exists():
                return PresentationResultCriteriaSerializer(scores, many=True).data
            return []
        except Exception:
            return []


class PresentationSerializer(serializers.ModelSerializer):
    results = PresentationResultSerializer(many=True, read_only=True)

    class Meta:
        model = Presentation
        fields = ['id', 'name', 'presentation_date', 'description', 'total_marks', 'pass_marks', 'created_at', 'updated_at', 'results']
        read_only_fields = ['created_at', 'updated_at', 'results']


class ProjectUserSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    project_title = serializers.CharField(source='project.title', read_only=True)
    
    def get_user_name(self, obj):
        return f"{obj.user.first_name} {obj.user.middle_name} {obj.user.last_name}".strip()
    
    class Meta:
        model = ProjectUser
        fields = ['id', 'project', 'project_title', 'user', 'user_name', 'role', 'joined_at']


class DuplicateFlagSerializer(serializers.ModelSerializer):
    project_title = serializers.CharField(source='project.title', read_only=True)
    similar_project_title = serializers.CharField(source='similar_project.title', read_only=True)
    reviewed_by_name = serializers.SerializerMethodField()
    project_registration_numbers = serializers.SerializerMethodField()
    similar_project_registration_numbers = serializers.SerializerMethodField()
    
    # ====== FIELDS FOR SIMILAR PROJECT INFO ======
    similar_project_author = serializers.SerializerMethodField()
    similar_project_mentor = serializers.SerializerMethodField()
    similar_project_description = serializers.CharField(source='similar_project.project_description', read_only=True, default='')
    similar_project_year = serializers.IntegerField(source='similar_project.year', read_only=True, default=None)
    similar_project_status = serializers.CharField(source='similar_project.status', read_only=True, default='')
    similar_project_type = serializers.CharField(source='similar_project.project_type.name', read_only=True, default='')
    
    # ====== Mentor comment on duplicate flag ======
    mentor_comment = serializers.CharField(allow_blank=True, required=False)
    
    def get_reviewed_by_name(self, obj):
        if obj.reviewed_by:
            return f"{obj.reviewed_by.first_name} {obj.reviewed_by.middle_name} {obj.reviewed_by.last_name}".strip()
        return None

    def _get_registration_numbers(self, project):
        registration_numbers = [
            relation.user.registration_number
            for relation in project.project_users.select_related('user').all()
            if relation.user.registration_number
        ]
        return registration_numbers

    def get_project_registration_numbers(self, obj):
        return self._get_registration_numbers(obj.project)

    def get_similar_project_registration_numbers(self, obj):
        return self._get_registration_numbers(obj.similar_project)
    
    def get_similar_project_author(self, obj):
        """Get author of similar project"""
        if obj.similar_project and obj.similar_project.user:
            user = obj.similar_project.user
            name_parts = [user.first_name or '', user.middle_name or '', user.last_name or '']
            full_name = ' '.join(filter(None, name_parts)).strip()
            if full_name:
                return full_name
            if user.username:
                return user.username
        return "Unknown"
    
    def get_similar_project_mentor(self, obj):
        """Get mentor of similar project"""
        if obj.similar_project and obj.similar_project.user:
            mentor = obj.similar_project.user.mentor
            if mentor:
                name_parts = [mentor.first_name or '', mentor.middle_name or '', mentor.last_name or '']
                full_name = ' '.join(filter(None, name_parts)).strip()
                if full_name:
                    return full_name
                if mentor.username:
                    return mentor.username
        return None
    
    class Meta:
        model = DuplicateFlag
        fields = [
            'id', 'project', 'project_title', 
            'similar_project', 'similar_project_title',
            'similar_project_author', 'similar_project_mentor',
            'similar_project_description', 'similar_project_year',
            'similar_project_status', 'similar_project_type',
            'project_registration_numbers', 'similar_project_registration_numbers',
            'similarity_score', 'reviewed', 'reviewed_by', 
            'reviewed_by_name', 'reviewed_at', 'created_at',
            'mentor_comment'
        ]


class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = [
            'duplicate_search_years_back',
            'duplicate_similarity_threshold',
            'duplicate_auto_flag_threshold',
            'duplicate_algorithm',
            'duplicate_semantic_weight',
            'duplicate_lexical_weight',
            'updated_at',
        ]
        read_only_fields = ['updated_at']

    def validate(self, attrs):
        algorithm = attrs.get('duplicate_algorithm', getattr(self.instance, 'duplicate_algorithm', 'HYBRID'))
        semantic_weight = attrs.get('duplicate_semantic_weight', getattr(self.instance, 'duplicate_semantic_weight', 0.7))
        lexical_weight = attrs.get('duplicate_lexical_weight', getattr(self.instance, 'duplicate_lexical_weight', 0.3))
        similarity_threshold = attrs.get('duplicate_similarity_threshold', getattr(self.instance, 'duplicate_similarity_threshold', 0.6))
        auto_flag_threshold = attrs.get('duplicate_auto_flag_threshold', getattr(self.instance, 'duplicate_auto_flag_threshold', 0.8))
        search_years_back = attrs.get('duplicate_search_years_back', getattr(self.instance, 'duplicate_search_years_back', 3))

        if not 0 <= similarity_threshold <= 1:
            raise serializers.ValidationError({'duplicate_similarity_threshold': 'Must be between 0 and 1.'})
        if not 0 <= auto_flag_threshold <= 1:
            raise serializers.ValidationError({'duplicate_auto_flag_threshold': 'Must be between 0 and 1.'})
        if auto_flag_threshold < similarity_threshold:
            raise serializers.ValidationError({'duplicate_auto_flag_threshold': 'Must be greater than or equal to the review threshold.'})
        if search_years_back < 1:
            raise serializers.ValidationError({'duplicate_search_years_back': 'Must be at least 1 year.'})

        if algorithm == 'HYBRID':
            if abs((semantic_weight + lexical_weight) - 1.0) > 0.001:
                raise serializers.ValidationError('Semantic and lexical weights must sum to 1.0 for HYBRID mode.')
        elif algorithm == 'EMBEDDING':
            attrs['duplicate_semantic_weight'] = 1.0
            attrs['duplicate_lexical_weight'] = 0.0
        elif algorithm == 'TFIDF':
            attrs['duplicate_semantic_weight'] = 0.0
            attrs['duplicate_lexical_weight'] = 1.0

        return attrs


# ============================================================
# SERIALIZER FOR SIMILAR PROJECTS
# ============================================================

class ProjectSimilarSerializer(serializers.ModelSerializer):
    """
    Serializer for displaying similar projects with mentor comments and similarity scores.
    Used by the Student Dashboard to show related projects and mentor feedback.
    """
    author_name = serializers.SerializerMethodField()
    mentor = serializers.SerializerMethodField()
    mentor_comment = serializers.SerializerMethodField()
    similarity_score = serializers.SerializerMethodField()
    description = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 
            'title', 
            'description', 
            'author_name', 
            'mentor', 
            'mentor_comment', 
            'similarity_score',
            'status',
            'year',
            'project_type_name'
        ]
    
    def get_author_name(self, obj):
        """Get student's full name from ProjectUser relations"""
        try:
            # Get the student user from ProjectUser where role is 'student'
            project_user = obj.project_users.filter(role='student').first()
            if project_user and project_user.user:
                user = project_user.user
                name_parts = [user.first_name or '', user.middle_name or '', user.last_name or '']
                return ' '.join(filter(None, name_parts)).strip() or user.username or 'Unknown Student'
        except Exception:
            pass
        
        # Fallback: try to get from user field
        if hasattr(obj, 'user') and obj.user:
            user = obj.user
            name_parts = [user.first_name or '', user.middle_name or '', user.last_name or '']
            full_name = ' '.join(filter(None, name_parts)).strip()
            if full_name:
                return full_name
            if user.username:
                return user.username
        
        return "Unknown Student"
    
    def get_mentor(self, obj):
        """Get mentor's full name"""
        try:
            # Get the mentor user from ProjectUser where role is 'mentor'
            project_user = obj.project_users.filter(role='mentor').first()
            if project_user and project_user.user:
                user = project_user.user
                name_parts = [user.first_name or '', user.middle_name or '', user.last_name or '']
                return ' '.join(filter(None, name_parts)).strip() or user.username or 'No mentor assigned'
        except Exception:
            pass
        
        # Fallback: try to get from user.mentor
        if hasattr(obj, 'user') and obj.user and hasattr(obj.user, 'mentor') and obj.user.mentor:
            mentor = obj.user.mentor
            name_parts = [mentor.first_name or '', mentor.middle_name or '', mentor.last_name or '']
            full_name = ' '.join(filter(None, name_parts)).strip()
            if full_name:
                return full_name
            if mentor.username:
                return mentor.username
        
        return "No mentor assigned"
    
    def get_mentor_comment(self, obj):
        """Get mentor's comment"""
        # Check if project has direct mentor_comment field
        if hasattr(obj, 'mentor_comment') and obj.mentor_comment:
            return obj.mentor_comment
        return None
    
    def get_description(self, obj):
        """Get project description/summary"""
        if hasattr(obj, 'project_description') and obj.project_description:
            return obj.project_description
        if hasattr(obj, 'description') and obj.description:
            return obj.description
        return ""
    
    def get_similarity_score(self, obj):
        """Calculate or retrieve similarity score"""
        # Check if similarity_score is stored in the object
        if hasattr(obj, 'similarity_score') and obj.similarity_score:
            if isinstance(obj.similarity_score, (int, float)):
                return f"{int(obj.similarity_score * 100)}%"
            return str(obj.similarity_score)
        
        return "N/A"


# ============================================================
# MAIN PROJECT SERIALIZER WITH AUTHOR AND MENTOR INFO
# ============================================================
# ====== FIX: user NA user_id ZIMEONGEWA ======

class ProjectSerializer(serializers.ModelSerializer):
    project_type = serializers.PrimaryKeyRelatedField(queryset=ProjectType.objects.all(), allow_null=True, required=False)
    project_type_name = serializers.CharField(source='project_type.name', read_only=True)
    documents = serializers.SerializerMethodField()
    presentation_results = serializers.SerializerMethodField()
    
    # ====== FIX: ADD user and user_id ======
    user = serializers.PrimaryKeyRelatedField(read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    
    # ====== AUTHOR FIELDS ======
    author_name = serializers.SerializerMethodField()
    mentor_info = serializers.SerializerMethodField()
    
    mentor_comment = serializers.CharField(
        allow_blank=True, 
        required=False, 
        allow_null=True,
        help_text="Mentor's feedback on the project"
    )
    
    project_users = serializers.SerializerMethodField()

    def get_documents(self, obj):
        return ProjectDocumentSerializer(obj.documents.all(), many=True, context=self.context).data

    def get_presentation_results(self, obj):
        return PresentationResultSerializer(obj.presentation_results.all(), many=True, context=self.context).data
    
    def get_author_name(self, obj):
        """Get author's full name"""
        if obj.user:
            name_parts = [obj.user.first_name or '', obj.user.middle_name or '', obj.user.last_name or '']
            full_name = ' '.join(filter(None, name_parts)).strip()
            if full_name:
                return full_name
            if obj.user.username:
                return obj.user.username
        return "Unknown"
    
    def get_mentor_info(self, obj):
        """Get mentor information"""
        if obj.user and obj.user.mentor:
            mentor = obj.user.mentor
            return {
                'id': mentor.id,
                'first_name': mentor.first_name,
                'middle_name': mentor.middle_name,
                'last_name': mentor.last_name,
                'email': mentor.email,
                'username': mentor.username
            }
        return None
    
    def get_project_users(self, obj):
        """Get project users"""
        project_users = obj.project_users.all()
        return ProjectUserSerializer(project_users, many=True).data

    class Meta:
        model = Project
        fields = [
            'id', 
            'user',
            'user_id',
            'title', 
            'project_type', 
            'project_type_name', 
            'main_objective', 
            'specific_objectives', 
            'project_description', 
            'implementation_details', 
            'year', 
            'status',
            'is_flagged_duplicate', 
            'duplicate_check_score', 
            'duplicate_keywords_matched',
            'created_at', 
            'updated_at', 
            'documents', 
            'presentation_results',
            'author_name', 
            'mentor_info', 
            'mentor_comment',
            'project_users'
        ]
        read_only_fields = [
            'title_embedding', 
            'objectives_embedding', 
            'combined_embedding', 
            'last_similarity_check', 
            'documents', 
            'presentation_results',
            'author_name', 
            'mentor_info',
            'user',
            'user_id',
            'project_users'
        ]


# ============================================================
# CRITERIA SERIALIZERS
# ============================================================

class PresentationCriteriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = PresentationCriteria
        fields = [
            'id', 'presentation', 'name', 'description', 
            'max_score', 'weight', 'order', 'is_required', 
            'options', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class PresentationResultCriteriaSerializer(serializers.ModelSerializer):
    criteria_name = serializers.CharField(source='criteria.name', read_only=True)
    criteria_max_score = serializers.FloatField(source='criteria.max_score', read_only=True)
    criteria_weight = serializers.FloatField(source='criteria.weight', read_only=True)

    class Meta:
        model = PresentationResultCriteria
        fields = [
            'id', 'result', 'criteria', 'criteria_name', 
            'criteria_max_score', 'criteria_weight', 
            'score', 'selected_option', 'comment', 
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']