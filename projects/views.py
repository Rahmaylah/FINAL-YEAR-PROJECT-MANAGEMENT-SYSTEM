import logging
from django.db.models import Q
from accounts import models
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAuthenticatedOrReadOnly, AllowAny
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.contrib.auth import authenticate
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone
from django.db import models as django_models

from accounts.models import User
from projects.models import Project, ProjectType, ProjectUser, DuplicateFlag, Presentation, PresentationResult
from projects.similarity import get_similarity_scorer
from core.models import SystemSettings

# ====== IMPORT CRITERIA MODELS ======
from projects.models import PresentationCriteria, PresentationResultCriteria

from .serializers import (
    UserSerializer, ProjectSerializer, ProjectTypeSerializer, ProjectUserSerializer,
    DuplicateFlagSerializer, SystemSettingsSerializer, ProjectDocumentSerializer,
    PresentationSerializer, PresentationResultSerializer, ProjectSimilarSerializer,
    PresentationCriteriaSerializer, PresentationResultCriteriaSerializer
)

logger = logging.getLogger(__name__)


def safe_to_list(embedding):
    """
    Safely convert any embedding to a list.
    Handles numpy arrays, Django VectorField, and other types.
    """
    if embedding is None:
        return None
    
    # If it's already a list, return it
    if isinstance(embedding, list):
        return embedding
    
    # If it has tolist method (numpy array or Django VectorField)
    if hasattr(embedding, 'tolist'):
        try:
            result = embedding.tolist()
            if isinstance(result, list):
                return result
        except Exception:
            pass
    
    # If it's a numpy array
    try:
        import numpy as np
        if isinstance(embedding, np.ndarray):
            return embedding.tolist()
    except ImportError:
        pass
    
    # If it's a tuple
    if isinstance(embedding, tuple):
        return list(embedding)
    
    # Return as is (might be None or something else)
    return embedding


class UserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing users.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        user = self.request.user
        
        # Kama user hajaingia, ona wote
        if not user.is_authenticated:
            return User.objects.all()
        
        # Staff au superuser wanaona wote
        if user.is_staff or user.is_superuser:
            queryset = User.objects.all()
        
        # Coordinator - anaona wote ila isipokuwa admin (is_staff=True)
        elif user.role == 'coordinator':
            queryset = User.objects.exclude(is_staff=True).exclude(is_superuser=True)
        
        # Mentor anaona wake tu na students wake (bila admin)
        elif user.role == 'mentor':
            queryset = User.objects.filter(
                Q(id=user.id) | Q(mentor_id=user.id)
            ).exclude(is_staff=True).exclude(is_superuser=True).distinct()
        
        # Student anaona wake tu
        else:
            queryset = User.objects.filter(id=user.id)

        # Filter kwa mentor
        mentor_id = self.request.query_params.get('mentor')
        if mentor_id is not None:
            if user.is_staff or user.is_superuser:
                queryset = User.objects.filter(mentor_id=mentor_id)
            elif user.role == 'coordinator':
                queryset = User.objects.filter(mentor_id=mentor_id).exclude(is_staff=True).exclude(is_superuser=True)
            elif user.role == 'mentor' and str(user.id) == str(mentor_id):
                queryset = User.objects.filter(mentor_id=mentor_id)
            else:
                queryset = queryset.none()

        # Filter kwa role
        role = self.request.query_params.get('role')
        if role is not None:
            queryset = queryset.filter(role=role)

        return queryset

    @action(detail=False, methods=['post'])
    def set_password(self, request):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        
        if not current_password or not new_password:
            return Response({'error': 'Current password and new password are required'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if not user.check_password(current_password):
            return Response({'error': 'Current password is incorrect'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Password changed successfully'}, 
                      status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def set_password_by_admin(self, request, pk=None):
        target_user = self.get_object()
        if not request.user.is_staff and request.user.role != 'coordinator':
            raise PermissionDenied("Only staff or coordinators can change another user's password.")

        new_password = request.data.get('new_password')
        if not new_password:
            return Response({'error': 'New password is required'},
                            status=status.HTTP_400_BAD_REQUEST)

        target_user.set_password(new_password)
        target_user.save()
        return Response({'message': 'Password changed successfully'},
                        status=status.HTTP_200_OK)


class ProjectTypeViewSet(viewsets.ModelViewSet):
    """ViewSet for managing project type options"""
    queryset = ProjectType.objects.all().order_by('name')
    serializer_class = ProjectTypeSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]


class ProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing projects.
    - list: Get all projects
    - retrieve: Get specific project
    - create: Submit new project (AUTO duplicate check)
    - update: Update project (AUTO duplicate check)
    - destroy: Delete project (owner or admin)
    - duplicate_check: Manually trigger duplicate detection for a project
    - similar: Get similar projects with mentor comments
    - similar-all: Get ALL similar projects (both sides of flag) - UNIQUE
    """
    queryset = Project.objects.all().order_by('-created_at')
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filterset_fields = ['project_type', 'year', 'status', 'is_flagged_duplicate']
    search_fields = ['title', 'main_objective', 'specific_objectives', 'project_description']
    
    def get_queryset(self):
        user = self.request.user
        
        # Kama hajaingia, rudisha empty (usalama)
        if not user.is_authenticated:
            return Project.objects.none()
        
        # Superuser au staff wanaona zote
        if user.is_superuser or user.is_staff:
            return Project.objects.all().order_by('-created_at')
        
        # ====== FIX: Mentor anaona projects zote za students wake ======
        if user.role == 'mentor':
            # Get all students under this mentor
            student_ids = User.objects.filter(mentor_id=user.id).values_list('id', flat=True)
            return Project.objects.filter(
                django_models.Q(user_id__in=student_ids) | 
                django_models.Q(project_users__user_id__in=student_ids)
            ).distinct().order_by('-created_at')
        
        # Student anaona projects zake TU
        if user.role == 'student':
            return Project.objects.filter(
                django_models.Q(user=user) | 
                django_models.Q(project_users__user=user)
            ).distinct().order_by('-created_at')
        
        # Coordinator na wengine wanaona zote
        return Project.objects.all().order_by('-created_at')
    
    def get_object(self):
        obj = super().get_object()
        user = self.request.user

        if not user.is_authenticated:
            raise PermissionDenied("Authentication required.")
        
        # Superuser au staff wanaona zote
        if user.is_superuser or user.is_staff:
            return obj
        
        # ====== FIX: Mentor anaweza kuona project yoyote ya students wake ======
        if user.role == 'mentor':
            # Get all student IDs under this mentor
            student_ids = User.objects.filter(mentor_id=user.id).values_list('id', flat=True)
            
            # Check if project belongs to one of mentor's students
            if obj.user_id in student_ids or ProjectUser.objects.filter(project=obj, user_id__in=student_ids).exists():
                return obj
            raise PermissionDenied("You do not have permission to access this project.")
        
        # Student anaweza kuona project yake TU
        if user.role == 'student':
            if ProjectUser.objects.filter(project=obj, user=user).exists() or obj.user_id == user.id:
                return obj
            raise PermissionDenied("You do not have permission to access this project.")
        
        # Coordinator wanaona zote
        return obj
    
    # ============================================================
    # ====== PERFORM_CREATE - AUTO DUPLICATE CHECK ======
    # ============================================================
    def perform_create(self, serializer):
        """Create project and automatically check for duplicates"""
        # ====== STEP 1: Save project first ======
        project = serializer.save(user=self.request.user)
        logger.info(f"Project {project.id} created: {project.title}")

        # ====== STEP 2: Run duplicate check ======
        self._run_duplicate_check(project)

    # ============================================================
    # ====== PERFORM_UPDATE - AUTO DUPLICATE CHECK ======
    # ============================================================
    def perform_update(self, serializer):
        """Update project - SKIP DUPLICATE CHECK FOR MENTOR"""
        # Get the existing project instance
        project = self.get_object()
        
        # ============================================================
        # ====== CHECK IF MENTOR IS UPDATING ======
        # ============================================================
        user = self.request.user
        is_mentor = user.role == 'mentor'
        updated_fields = set(serializer.validated_data.keys())
        
        # ====== FIX: ALLOW ALL FIELDS MENTOR MIGHT UPDATE ======
        mentor_allowed_fields = {
            'status', 
            'mentor_comment',
            'marks', 
            'comment', 
            'criteria_scores',
            'criteria_total', 
            'is_graded_by_criteria',
            'reviewer',
            'project'
        }
        
        # ============================================================
        # ====== IF MENTOR IS UPDATING, SKIP DUPLICATE CHECK ======
        # ============================================================
        if is_mentor and updated_fields.issubset(mentor_allowed_fields):
            from projects.models import disable_duplicate_check, enable_duplicate_check
            
            # ====== DISABLE SIGNAL ======
            disable_duplicate_check()
            logger.info("DUPLICATE CHECK SIGNAL DISABLED for mentor update")
            
            try:
                # ====== SAVE PROJECT ======
                updated_project = serializer.save()
                logger.info(f"Project {updated_project.id} updated: {updated_project.title}")
                
                # ====== GET ORIGINAL PROJECT STATE ======
                original_project = Project.objects.get(id=project.id)
                original_flagged = original_project.is_flagged_duplicate
                original_score = original_project.duplicate_check_score
                
                logger.info(f"Original state: flagged={original_flagged}, score={original_score}")
                logger.info(f"Updated fields: {updated_fields}")
                
                # ====== FORCE RESET TO ORIGINAL FLAG STATE ======
                if not original_flagged:
                    # Was UNFLAGGED - keep UNFLAGGED
                    Project.objects.filter(id=updated_project.id).update(
                        is_flagged_duplicate=False,
                        duplicate_check_score=None,
                        duplicate_keywords_matched=[]
                    )
                    # ====== ONLY DELETE FLAGS IF PROJECT WAS UNFLAGGED ======
                    DuplicateFlag.objects.filter(project=updated_project).delete()
                    DuplicateFlag.objects.filter(similar_project=updated_project).delete()
                    logger.info(f"FORCED project {updated_project.id} to remain UNFLAGGED")
                else:
                    # ====== Was FLAGGED - keep FLAGGED ======
                    Project.objects.filter(id=updated_project.id).update(
                        is_flagged_duplicate=True,
                        duplicate_check_score=original_score
                    )
                    # ====== DO NOT DELETE FLAGS! ======
                    logger.info(f"FORCED project {updated_project.id} to remain FLAGGED with score {original_score}")
                
                # Update instance
                updated_project.is_flagged_duplicate = original_flagged
                updated_project.duplicate_check_score = original_score
                
            finally:
                # ====== ENABLE SIGNAL ======
                enable_duplicate_check()
                logger.info("DUPLICATE CHECK SIGNAL ENABLED")
            
            return

        # ============================================================
        # ====== NORMAL UPDATE (NOT MENTOR) ======
        # ============================================================
        
        # Save project
        updated_project = serializer.save()
        logger.info(f"Project {updated_project.id} updated: {updated_project.title}")

        # Regenerate embeddings if content changed
        fields_to_check = ['title', 'main_objective', 'project_description', 'specific_objectives']
        content_changed = False
        
        for field in fields_to_check:
            old_value = getattr(project, field)
            new_value = getattr(updated_project, field)
            if old_value != new_value:
                content_changed = True
                break
        
        if content_changed:
            from projects.utils import generate_project_embeddings
            embeddings = generate_project_embeddings(
                title=updated_project.title,
                objectives=updated_project.main_objective,
                description=updated_project.project_description
            )
            
            if embeddings:
                updated_project.title_embedding = embeddings.get('title_embedding')
                updated_project.objectives_embedding = embeddings.get('objectives_embedding')
                updated_project.combined_embedding = embeddings.get('combined_embedding')
                updated_project.last_similarity_check = timezone.now()
                updated_project.save(update_fields=[
                    'title_embedding', 'objectives_embedding', 
                    'combined_embedding', 'last_similarity_check'
                ])
                logger.info(f"Regenerated embeddings for project {updated_project.id}")
            else:
                logger.warning(f"Failed to regenerate embeddings for project {updated_project.id}")

        # Run duplicate check ONLY if content changed
        if content_changed:
            self._run_duplicate_check(updated_project)
        else:
            logger.info(f"No content changes - skipping duplicate check for project {updated_project.id}")

        
    def _run_duplicate_check(self, project):
        """
        Common function to run duplicate check for a project.
        """
        try:
            # ====== STEP 1: Generate embeddings if missing ======
            if project.combined_embedding is None:
                from projects.utils import generate_project_embeddings
                embeddings = generate_project_embeddings(
                    title=project.title,
                    objectives=project.main_objective,
                    description=project.project_description
                )
                if embeddings:
                    project.title_embedding = embeddings.get('title_embedding')
                    project.objectives_embedding = embeddings.get('objectives_embedding')
                    project.combined_embedding = embeddings.get('combined_embedding')
                    project.last_similarity_check = timezone.now()
                    project.save(update_fields=[
                        'title_embedding', 'objectives_embedding', 
                        'combined_embedding', 'last_similarity_check'
                    ])
                    logger.info(f"Generated embeddings for project {project.id}")
                else:
                    logger.warning(f"Failed to generate embeddings for project {project.id}")
                    return

            # ====== STEP 2: Get settings ======
            settings = SystemSettings.get_solo()
            auto_flag_threshold = settings.duplicate_auto_flag_threshold or 0.5

            # ====== STEP 3: Find similar projects (EXCLUDE SAME USER) ======
            try:
                from pgvector.django import CosineDistance
                
                similar_projects = Project.objects.exclude(id=project.id).exclude(
                    combined_embedding__isnull=True
                ).exclude(
                    user=project.user
                ).annotate(
                    distance=CosineDistance('combined_embedding', project.combined_embedding)
                ).filter(
                    distance__lt=1 - 0.3
                ).order_by('distance')[:10]
                
            except Exception as e:
                logger.error(f"pgvector error: {e}")
                similar_projects = []

            # ====== STEP 4: Check for duplicates ======
            max_similarity = 0.0
            best_match = None
            matched_keywords = []

            for match in similar_projects:
                similarity = 1 - match.distance
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_match = match

            # ====== STEP 5: Keyword matching ======
            if best_match and max_similarity >= 0.3:
                text1 = f"{project.title} {project.main_objective} {project.project_description or ''}"
                text2 = f"{best_match.title} {best_match.main_objective} {best_match.project_description or ''}"
                keywords1 = set(extract_keywords(text1))
                keywords2 = set(extract_keywords(text2))
                common = keywords1.intersection(keywords2)
                matched_keywords = list(common)[:10]

            # ============================================================
            # ====== CHECK IF THIS IS THE FIRST PROJECT ======
            # ============================================================
            
            older_projects = Project.objects.filter(
                Q(user=project.user) | Q(project_users__user=project.user)
            ).exclude(id=project.id).filter(created_at__lt=project.created_at).exists()
            
            should_flag = False
            
            if best_match and max_similarity >= auto_flag_threshold:
                if older_projects:
                    should_flag = True
                    logger.info(f"Project {project.id} has older projects - FLAGGING")
                else:
                    logger.info(f"Project {project.id} is FIRST - NOT FLAGGING")

            # ============================================================
            # ====== CRITICAL FIX: ALWAYS CREATE DUPLICATEFLAG ======
            # ============================================================
            
            if best_match and max_similarity >= auto_flag_threshold:
                # ====== FLAG 1: Tree -> Forest ======
                flag1, created1 = DuplicateFlag.objects.get_or_create(
                    project=project,
                    similar_project=best_match,
                    defaults={
                        'similarity_score': max_similarity,
                    }
                )
                
                if not created1:
                    flag1.similarity_score = max_similarity
                    flag1.save()
                    logger.info(f"Updated flag: {project.id} -> {best_match.id}")
                else:
                    logger.info(f"Created flag: {project.id} -> {best_match.id}")
                
                # ====== FLAG 2: Forest -> Tree (BOTH SIDES) ======
                flag2, created2 = DuplicateFlag.objects.get_or_create(
                    project=best_match,
                    similar_project=project,
                    defaults={
                        'similarity_score': max_similarity,
                    }
                )
                
                if not created2:
                    flag2.similarity_score = max_similarity
                    flag2.save()
                    logger.info(f"Updated reverse flag: {best_match.id} -> {project.id}")
                else:
                    logger.info(f"Created reverse flag: {best_match.id} -> {project.id}")
                
                # ====== FLAG THE PROJECT IF IT'S SECOND+ ======
                if should_flag:
                    project.is_flagged_duplicate = True
                    project.duplicate_check_score = max_similarity
                    project.duplicate_keywords_matched = matched_keywords
                    project.last_similarity_check = timezone.now()
                    
                    Project.objects.filter(id=project.id).update(
                        is_flagged_duplicate=True,
                        duplicate_check_score=max_similarity,
                        duplicate_keywords_matched=matched_keywords,
                        last_similarity_check=timezone.now()
                    )
                    
                    if not best_match.is_flagged_duplicate:
                        best_match.is_flagged_duplicate = True
                        best_match.duplicate_check_score = max_similarity
                        best_match.save(update_fields=['is_flagged_duplicate', 'duplicate_check_score'])
                        logger.info(f"Also flagged other project {best_match.id} for mentor")
                    
                    logger.info(f"SECOND+ Project {project.id} FLAGGED! Score: {max_similarity:.3f}")
                else:
                    # ====== FIRST PROJECT - NEVER FLAGGED ======
                    project.is_flagged_duplicate = False
                    project.duplicate_check_score = None
                    project.duplicate_keywords_matched = []
                    project.last_similarity_check = timezone.now()
                    
                    Project.objects.filter(id=project.id).update(
                        is_flagged_duplicate=False,
                        duplicate_check_score=None,
                        duplicate_keywords_matched=[],
                        last_similarity_check=timezone.now()
                    )
                    
                    logger.info(f"FIRST Project {project.id} - NOT FLAGGED (flag record exists)")
            else:
                # ====== NO DUPLICATE FOUND ======
                project.is_flagged_duplicate = False
                project.duplicate_check_score = None
                project.duplicate_keywords_matched = []
                project.last_similarity_check = timezone.now()
                
                Project.objects.filter(id=project.id).update(
                    is_flagged_duplicate=False,
                    duplicate_check_score=None,
                    duplicate_keywords_matched=[],
                    last_similarity_check=timezone.now()
                )
                
                DuplicateFlag.objects.filter(project=project).delete()
                DuplicateFlag.objects.filter(similar_project=project).delete()
                
                logger.info(f"Project {project.id} - no duplicates")

            # ============================================================
            # ====== VERIFY FLAG EXISTS ======
            # ============================================================
            
            if should_flag:
                flag_exists = DuplicateFlag.objects.filter(
                    Q(project=project) | Q(similar_project=project)
                ).exists()
                
                if not flag_exists:
                    logger.error(f"Project {project.id} should be flagged but NO DuplicateFlag exists!")
                    if best_match:
                        DuplicateFlag.objects.create(
                            project=project,
                            similar_project=best_match,
                            similarity_score=max_similarity
                        )
                        DuplicateFlag.objects.create(
                            project=best_match,
                            similar_project=project,
                            similarity_score=max_similarity
                        )
                        logger.info(f"FORCE CREATED flags for {project.id} <-> {best_match.id}")

        except Exception as e:
            logger.error(f"Error in duplicate check for project {project.id}: {e}")
            import traceback
            traceback.print_exc()

    # ============================================================
    # ====== MANUAL DUPLICATE CHECK (BUTTON) ======
    # ============================================================
    @action(detail=True, methods=['post'])
    def duplicate_check(self, request, pk=None):
        """
        Manually trigger duplicate detection for a project.
        """
        try:
            project = self.get_object()
            
            # Run duplicate check
            self._run_duplicate_check(project)
            
            # Refresh project data
            project.refresh_from_db()
            
            return Response({
                'project_id': project.id,
                'project_title': project.title,
                'is_flagged': project.is_flagged_duplicate,
                'duplicate_check_score': project.duplicate_check_score,
                'duplicate_keywords_matched': project.duplicate_keywords_matched,
                'message': 'Duplicate check completed successfully'
            })
            
        except Exception as e:
            logger.error(f"Duplicate check error for project {pk}: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': str(e),
                'project_id': pk
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['post'])
    def bulk_duplicate_check(self, request):
        project_ids = request.data.get('project_ids', [])
        
        if not project_ids:
            projects = Project.objects.all()
        else:
            projects = Project.objects.filter(id__in=project_ids)
        
        results = []
        total_auto_flagged = 0
        
        for project in projects:
            try:
                # Run duplicate check for each project
                self._run_duplicate_check(project)
                project.refresh_from_db()
                
                results.append({
                    'project_id': project.id,
                    'project_title': project.title,
                    'is_flagged': project.is_flagged_duplicate,
                    'score': project.duplicate_check_score,
                    'processed': True
                })
                
                if project.is_flagged_duplicate:
                    total_auto_flagged += 1
                
            except Exception as e:
                logger.error(f"Failed to process project {project.id}: {e}")
                results.append({
                    'project_id': project.id,
                    'project_title': project.title,
                    'error': str(e),
                    'processed': False
                })
        
        return Response({
            'total_projects_processed': len(results),
            'total_auto_flagged': total_auto_flagged,
            'results': results
        })
    
    @action(detail=False, methods=['get'])
    def flagged(self, request):
        flagged_projects = Project.objects.filter(is_flagged_duplicate=True)
        serializer = self.get_serializer(flagged_projects, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'], parser_classes=[MultiPartParser, FormParser])
    def upload_document(self, request, pk=None):
        project = self.get_object()

        if not request.user.is_authenticated:
            raise PermissionDenied("Authentication required to upload documents.")

        serializer = ProjectDocumentSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save(project=project, uploaded_by=request.user)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['get'], url_path='my')
    def my_projects(self, request):
        user = request.user
        projects = Project.objects.filter(project_users__user=user).distinct()
        serializer = self.get_serializer(projects, many=True)
        return Response(serializer.data)

    # ============================================================
    # ====== GET SIMILAR PROJECTS WITH MENTOR COMMENTS ======
    # ============================================================
    @action(detail=True, methods=['get'], url_path='similar')
    def similar_projects(self, request, pk=None):
        """
        Get projects similar to this project with mentor comments and similarity scores.
        """
        try:
            current_project = self.get_object()
            
            # Get query parameters for filtering
            limit = int(request.query_params.get('limit', 10))
            include_proposed = request.query_params.get('include_proposed', 'false').lower() == 'true'
            
            # Build query for similar projects
            query = Q()
            
            # Same project type
            if current_project.project_type:
                query |= Q(project_type=current_project.project_type)
            
            # Extract keywords from title
            title_keywords = str(current_project.title).split()[:5] if current_project.title else []
            for keyword in title_keywords:
                if len(keyword) > 3:
                    query |= Q(title__icontains=keyword)
                    if current_project.project_description:
                        query |= Q(project_description__icontains=keyword)
                    if current_project.main_objective:
                        query |= Q(main_objective__icontains=keyword)
            
            if not query:
                query = Q(project_type=current_project.project_type) if current_project.project_type else Q()
            
            similar_projects = Project.objects.filter(query)
            similar_projects = similar_projects.exclude(id=current_project.id)
            
            if not include_proposed:
                similar_projects = similar_projects.exclude(status='proposed')
            
            similar_projects = similar_projects.distinct()
            
            if current_project.project_type:
                similar_projects = similar_projects.extra(
                    select={'same_type': "CASE WHEN project_type_id = %s THEN 1 ELSE 0 END" % current_project.project_type.id}
                ).order_by('-same_type', '-created_at')
            else:
                similar_projects = similar_projects.order_by('-created_at')
            
            similar_projects = similar_projects[:limit]
            
            serializer = ProjectSimilarSerializer(
                similar_projects, 
                many=True, 
                context={
                    'request': request, 
                    'view': {'kwargs': {'project_id': current_project.id}}
                }
            )
            
            return Response({
                'count': len(similar_projects),
                'results': serializer.data,
                'project_id': current_project.id,
                'project_title': current_project.title
            }, status=status.HTTP_200_OK)
            
        except Project.DoesNotExist:
            return Response({
                'error': 'Project not found',
                'results': []
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching similar projects: {e}")
            return Response({
                'error': str(e),
                'results': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ============================================================
    # ====== GET ALL SIMILAR PROJECTS (BOTH SIDES + EMBEDDINGS) ======
    # ============================================================
    @action(detail=True, methods=['get'], url_path='similar-all')
    def similar_all(self, request, pk=None):
        """
        Get ALL similar projects for a given project.
        """
        try:
            project = self.get_object()
            
            # ====== STEP 1: Get flags ======
            flags = DuplicateFlag.objects.filter(
                Q(project=project) | Q(similar_project=project)
            ).select_related('project', 'similar_project', 'project__user', 'similar_project__user')
            
            # ====== STEP 2: If no flags, find similar using embeddings ======
            if not flags.exists():
                logger.info(f"No flags found for project {project.id}, searching via embeddings...")
                
                try:
                    from pgvector.django import CosineDistance
                    
                    # Find similar projects using embeddings
                    similar_projects = Project.objects.exclude(id=project.id).exclude(
                        combined_embedding__isnull=True
                    ).exclude(
                        user=project.user
                    ).annotate(
                        distance=CosineDistance('combined_embedding', project.combined_embedding)
                    ).filter(
                        distance__lt=1 - 0.3
                    ).order_by('distance')[:5]
                    
                    if similar_projects.exists():
                        logger.info(f"Found {similar_projects.count()} similar projects via embeddings")
                        
                        results = []
                        for match in similar_projects:
                            similarity = 1 - match.distance
                            
                            author_name = "Unknown"
                            if match.user:
                                name_parts = [
                                    match.user.first_name or '',
                                    match.user.middle_name or '',
                                    match.user.last_name or ''
                                ]
                                author_name = ' '.join(filter(None, name_parts)).strip() or match.user.username or "Unknown"
                            
                            mentor_name = "N/A"
                            if match.user and match.user.mentor:
                                mentor = match.user.mentor
                                name_parts = [
                                    mentor.first_name or '',
                                    mentor.middle_name or '',
                                    mentor.last_name or ''
                                ]
                                mentor_name = ' '.join(filter(None, name_parts)).strip() or mentor.username or "N/A"
                            
                            project_type_name = "N/A"
                            if match.project_type:
                                project_type_name = match.project_type.name
                            
                            registration_numbers = []
                            project_users = ProjectUser.objects.filter(project=match).select_related('user')
                            for pu in project_users:
                                if pu.user and pu.user.registration_number:
                                    registration_numbers.append(pu.user.registration_number)
                            
                            results.append({
                                'id': match.id,
                                'title': match.title or 'Untitled',
                                'description': match.project_description or '',
                                'author_name': author_name,
                                'mentor': mentor_name,
                                'mentor_comment': match.mentor_comment,
                                'similarity_score': similarity,
                                'status': match.status or 'proposed',
                                'year': match.year,
                                'project_type_name': project_type_name,
                                'flag_id': None,
                                'reviewed': False,
                                'flag_created_at': None,
                                'registration_numbers': registration_numbers,
                            })
                        
                        results.sort(key=lambda x: x['similarity_score'] or 0, reverse=True)
                        
                        return Response({
                            'count': len(results),
                            'results': results,
                            'project_id': project.id,
                            'project_title': project.title
                        })
                        
                except Exception as e:
                    logger.error(f"Error finding similar projects via embeddings: {e}")
                
                return Response({
                    'count': 0,
                    'results': [],
                    'project_id': project.id,
                    'message': 'No similar projects found'
                })
            
            # ====== STEP 3: Process flags ======
            seen_project_ids = set()
            similar_projects_data = []
            
            for flag in flags:
                if flag.project.id == project.id:
                    other_project = flag.similar_project
                else:
                    other_project = flag.project
                
                if not other_project:
                    continue
                
                if other_project.id in seen_project_ids:
                    continue
                seen_project_ids.add(other_project.id)
                
                author_name = "Unknown"
                if other_project.user:
                    name_parts = [
                        other_project.user.first_name or '',
                        other_project.user.middle_name or '',
                        other_project.user.last_name or ''
                    ]
                    author_name = ' '.join(filter(None, name_parts)).strip() or other_project.user.username or "Unknown"
                
                mentor_name = "N/A"
                if other_project.user and other_project.user.mentor:
                    mentor = other_project.user.mentor
                    name_parts = [
                        mentor.first_name or '',
                        mentor.middle_name or '',
                        mentor.last_name or ''
                    ]
                    mentor_name = ' '.join(filter(None, name_parts)).strip() or mentor.username or "N/A"
                
                mentor_comment = other_project.mentor_comment if other_project.mentor_comment else None
                
                project_type_name = "N/A"
                if other_project.project_type:
                    project_type_name = other_project.project_type.name
                
                registration_numbers = []
                project_users = ProjectUser.objects.filter(project=other_project).select_related('user')
                for pu in project_users:
                    if pu.user and pu.user.registration_number:
                        registration_numbers.append(pu.user.registration_number)
                
                similar_projects_data.append({
                    'id': other_project.id,
                    'title': other_project.title or 'Untitled',
                    'description': other_project.project_description or '',
                    'author_name': author_name,
                    'mentor': mentor_name,
                    'mentor_comment': mentor_comment,
                    'similarity_score': flag.similarity_score,
                    'status': other_project.status or 'proposed',
                    'year': other_project.year,
                    'project_type_name': project_type_name,
                    'flag_id': flag.id,
                    'reviewed': flag.reviewed,
                    'flag_created_at': flag.created_at,
                    'registration_numbers': registration_numbers,
                })
            
            similar_projects_data.sort(key=lambda x: x['similarity_score'] or 0, reverse=True)
            
            return Response({
                'count': len(similar_projects_data),
                'results': similar_projects_data,
                'project_id': project.id,
                'project_title': project.title
            })
            
        except Project.DoesNotExist:
            return Response({
                'error': 'Project not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching all similar projects: {e}")
            import traceback
            traceback.print_exc()
            return Response({
                'error': str(e),
                'results': []
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # ============================================================
    # ====== ADVANCED SIMILAR PROJECTS ======
    # ============================================================
    @action(detail=True, methods=['get'], url_path='similar-advanced')
    def similar_projects_advanced(self, request, pk=None):
        """
        Advanced similarity matching using TF-IDF if available.
        """
        try:
            current_project = self.get_object()
            
            try:
                from sklearn.feature_extraction.text import TfidfVectorizer
                from sklearn.metrics.pairwise import cosine_similarity
                import numpy as np
                
                all_projects = Project.objects.exclude(id=current_project.id).exclude(status='proposed')
                
                if not all_projects.exists():
                    return Response({
                        'count': 0,
                        'results': [],
                        'project_id': current_project.id,
                        'project_title': current_project.title
                    })
                
                corpus = []
                project_list = []
                
                for proj in all_projects:
                    text = f"{proj.title} {proj.main_objective or ''} {proj.project_description or ''}"
                    corpus.append(text)
                    project_list.append(proj)
                
                current_text = f"{current_project.title} {current_project.main_objective or ''} {current_project.project_description or ''}"
                corpus.append(current_text)
                
                vectorizer = TfidfVectorizer(stop_words='english', max_features=100)
                tfidf_matrix = vectorizer.fit_transform(corpus)
                
                similarity_scores = cosine_similarity(tfidf_matrix[-1:], tfidf_matrix[:-1])[0]
                
                scored_projects = []
                for i, (proj, score) in enumerate(zip(project_list, similarity_scores)):
                    if score > 0.05:
                        scored_projects.append((proj, score))
                
                scored_projects.sort(key=lambda x: x[1], reverse=True)
                
                limit = int(request.query_params.get('limit', 10))
                top_projects = [proj for proj, _ in scored_projects[:limit]]
                top_scores = [score for _, score in scored_projects[:limit]]
                
                serializer = ProjectSimilarSerializer(
                    top_projects, 
                    many=True, 
                    context={'request': request, 'view': {'kwargs': {'project_id': current_project.id}}}
                )
                
                results = serializer.data
                for i, item in enumerate(results):
                    if i < len(top_scores):
                        score_percentage = int(top_scores[i] * 100)
                        item['similarity_score'] = f"{score_percentage}%"
                    else:
                        item['similarity_score'] = "N/A"
                
                return Response({
                    'count': len(results),
                    'results': results,
                    'project_id': current_project.id,
                    'project_title': current_project.title,
                    'method': 'advanced'
                })
                
            except ImportError:
                logger.warning("scikit-learn not available, falling back to basic similarity")
                return self.similar_projects(request, pk)
                
        except Project.DoesNotExist:
            return Response({
                'error': 'Project not found',
                'results': []
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error in advanced similarity: {e}")
            return self.similar_projects(request, pk)

    # ============================================================
    # ====== AVAILABLE MENTORS ENDPOINT ======
    # ============================================================
    @action(detail=False, methods=['get'], url_path='available_mentors')
    def available_mentors(self, request):
        """
        Get mentors available for assignment based on capacity and specialization.
        """
        project_type_id = request.query_params.get('project_type_id')
        project_id = request.query_params.get('project_id')
        
        if project_id:
            try:
                project = Project.objects.get(id=project_id)
                if project.project_type:
                    project_type_id = project.project_type.id
            except Project.DoesNotExist:
                pass
        
        mentors = User.objects.filter(role='mentor')
        
        available_mentors = []
        
        for mentor in mentors:
            current_students = User.objects.filter(mentor=mentor, role='student').count()
            max_students = mentor.max_students or 5
            available_slots = max_students - current_students
            
            if available_slots <= 0:
                continue
            
            has_specialization = False
            if project_type_id:
                has_specialization = mentor.specialization and mentor.specialization.id == int(project_type_id)
                if not has_specialization:
                    if mentor.specialization:
                        continue
            else:
                has_specialization = True
            
            available_mentors.append({
                'id': mentor.id,
                'name': f"{mentor.first_name} {mentor.last_name}",
                'username': mentor.username,
                'email': mentor.email,
                'max_students': max_students,
                'current_students': current_students,
                'available_slots': available_slots,
                'capacity_status': 'FULL' if available_slots <= 0 else f'{available_slots} slots left',
                'specialization': mentor.specialization.name if mentor.specialization else None,
                'has_specialization': has_specialization,
                'mentor_bio': mentor.mentor_bio
            })
        
        available_mentors.sort(key=lambda x: x['available_slots'], reverse=True)
        
        return Response({
            'mentors': available_mentors,
            'total': len(available_mentors),
            'project_type_id': project_type_id
        })

    # ============================================================
    # ====== BULK ACTION ENDPOINT (with CSRF exempt) ======
    # ============================================================
    @method_decorator(csrf_exempt, name='dispatch')
    @action(detail=False, methods=['post'], url_path='bulk_action')
    def bulk_action(self, request):
        """
        Perform bulk actions on multiple projects.
        """
        user = request.user
        
        # Check permissions
        if user.role not in ['coordinator', 'admin'] and not user.is_staff:
            raise PermissionDenied("Only coordinators and admins can perform bulk actions.")
        
        # Get data
        action = request.data.get('action')
        project_ids = request.data.get('project_ids', [])
        data = request.data.get('data', {})
        
        # Validate
        if not action:
            return Response(
                {'error': 'Action is required. Available actions: approve, reject, change_status, assign_mentor, auto_assign_mentor, export, delete'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not project_ids:
            return Response(
                {'error': 'No projects selected. Please provide project_ids.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get projects
        projects = Project.objects.filter(id__in=project_ids)
        
        if not projects.exists():
            return Response(
                {'error': 'No valid projects found with the provided IDs.'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Perform action
        results = []
        errors = []
        processed_count = 0
        
        for project in projects:
            try:
                result = self._process_bulk_action(project, action, data, user)
                results.append(result)
                processed_count += 1
            except Exception as e:
                errors.append({
                    'id': project.id,
                    'title': project.title,
                    'error': str(e)
                })
        
        return Response({
            'success': len(errors) == 0,
            'processed': processed_count,
            'failed': len(errors),
            'total': len(projects),
            'results': results,
            'errors': errors,
            'action': action
        }, status=status.HTTP_200_OK)

    def _process_bulk_action(self, project, action, data, user):
        """Process a single bulk action for a project."""
        result = {
            'id': project.id,
            'title': project.title,
            'status': 'success'
        }
        
        if action == 'approve':
            project.status = 'approved'
            project.save()
            result['message'] = 'Project approved successfully.'
            
        elif action == 'reject':
            project.status = 'rejected'
            comment = data.get('comment', '')
            if comment:
                project.mentor_comment = comment
            project.save()
            result['message'] = 'Project rejected successfully.'
            if comment:
                result['comment'] = comment
            
        elif action == 'change_status':
            new_status = data.get('status')
            if not new_status:
                raise ValueError('Status is required for change_status action.')
            
            valid_statuses = ['proposed', 'approved', 'rejected', 'completed']
            if new_status not in valid_statuses:
                raise ValueError(f'Invalid status. Must be one of: {", ".join(valid_statuses)}')
            
            project.status = new_status
            project.save()
            result['message'] = f'Status changed to {new_status}.'
            result['new_status'] = new_status
            
        elif action == 'assign_mentor':
            # ====== MANUAL ASSIGNMENT ======
            mentor_id = data.get('mentor_id')
            if not mentor_id:
                raise ValueError('Mentor ID is required for assign_mentor action.')
            
            try:
                mentor = User.objects.get(id=mentor_id, role='mentor')
            except User.DoesNotExist:
                raise ValueError(f'Mentor with ID {mentor_id} not found or is not a mentor.')
            
            # Check mentor capacity
            current_students = User.objects.filter(mentor=mentor, role='student').count()
            max_students = mentor.max_students or 5
            available_slots = max_students - current_students
            
            if available_slots <= 0:
                raise ValueError(f'Mentor {mentor.first_name} {mentor.last_name} is FULL. Current: {current_students}/{max_students}')
            
            # Get all students in this project
            project_users = ProjectUser.objects.filter(project=project)
            assigned_count = 0
            students_assigned = []
            
            for pu in project_users:
                if pu.user.role == 'student' and pu.user.mentor != mentor:
                    if available_slots <= 0:
                        result['warning'] = f'Stopped at {assigned_count} students. Mentor is full.'
                        break
                    pu.user.mentor = mentor
                    pu.user.save()
                    assigned_count += 1
                    available_slots -= 1
                    students_assigned.append({
                        'id': pu.user.id,
                        'name': pu.user.get_full_name(),
                        'registration_number': pu.user.registration_number
                    })
            
            # Also assign to the project owner if they are a student
            if project.user and project.user.role == 'student' and project.user.mentor != mentor:
                if available_slots > 0:
                    project.user.mentor = mentor
                    project.user.save()
                    assigned_count += 1
                    students_assigned.append({
                        'id': project.user.id,
                        'name': project.user.get_full_name(),
                        'registration_number': project.user.registration_number
                    })
            
            result['message'] = f'Assigned mentor {mentor.first_name} {mentor.last_name} to {assigned_count} students.'
            result['assigned_count'] = assigned_count
            result['mentor_id'] = mentor_id
            result['mentor_name'] = f"{mentor.first_name} {mentor.last_name}"
            result['students_assigned'] = students_assigned
            result['mentor_capacity'] = {
                'current': current_students + assigned_count,
                'max': max_students,
                'available': available_slots
            }
            
        elif action == 'auto_assign_mentor':
            # ====== AUTO ASSIGNMENT ======
            result = self._auto_assign_mentor_to_project(project)
            
        elif action == 'export':
            result['message'] = 'Project exported successfully.'
            result['export_data'] = {
                'id': project.id,
                'title': project.title,
                'status': project.status,
                'project_type': project.project_type.name if project.project_type else None,
                'main_objective': project.main_objective,
                'year': project.year,
                'created_at': project.created_at.isoformat(),
                'student': project.user.username if project.user else None,
            }
            
        elif action == 'delete':
            project_title = project.title
            project.delete()
            result['message'] = f'Project "{project_title}" deleted successfully.'
            
        else:
            raise ValueError(f'Unknown action: {action}')
        
        return result

    def _auto_assign_mentor_to_project(self, project):
        """
        Auto-assign the best mentor to a project based on:
        1. Specialization match
        2. Available capacity
        3. Current load balancing
        """
        result = {
            'id': project.id,
            'title': project.title,
            'status': 'success'
        }
        
        # Get project type
        project_type = project.project_type
        
        # Get all mentors
        mentors = User.objects.filter(role='mentor')
        
        if not mentors.exists():
            raise ValueError('No mentors available in the system.')
        
        # Score each mentor
        mentor_scores = []
        
        for mentor in mentors:
            # Check capacity
            current_students = User.objects.filter(mentor=mentor, role='student').count()
            max_students = mentor.max_students or 5
            available_slots = max_students - current_students
            
            if available_slots <= 0:
                continue
            
            # Calculate score
            score = 0
            reasons = []
            
            # 1. Specialization match (40 points)
            if project_type and mentor.specialization:
                if mentor.specialization.id == project_type.id:
                    score += 40
                    reasons.append(f'Expert in {project_type.name}')
                else:
                    score += 10
                    reasons.append(f'Specialized in {mentor.specialization.name}')
            elif not mentor.specialization:
                score += 20
                reasons.append('General mentor (no specialization)')
            else:
                score += 5
                reasons.append('No matching specialization')
            
            # 2. Available slots (30 points)
            score += min(available_slots * 6, 30)
            reasons.append(f'{available_slots} slots available')
            
            # 3. Current load balancing (20 points)
            load_score = max(0, 20 - (current_students * 2))
            score += load_score
            reasons.append(f'{current_students} current students')
            
            # 4. Specialization exists (10 points)
            if mentor.specialization:
                score += 10
                reasons.append('Has specialization defined')
            
            mentor_scores.append({
                'mentor': mentor,
                'score': score,
                'available_slots': available_slots,
                'current_students': current_students,
                'max_students': max_students,
                'reasons': reasons
            })
        
        if not mentor_scores:
            raise ValueError('No available mentors with capacity. All mentors are full.')
        
        # Sort by score (highest first)
        mentor_scores.sort(key=lambda x: x['score'], reverse=True)
        
        # Get the best mentor
        best = mentor_scores[0]
        mentor = best['mentor']
        available_slots = best['available_slots']
        
        # Get all students in this project
        project_users = ProjectUser.objects.filter(project=project)
        assigned_count = 0
        students_assigned = []
        
        for pu in project_users:
            if pu.user.role == 'student' and pu.user.mentor != mentor:
                if available_slots <= 0:
                    break
                pu.user.mentor = mentor
                pu.user.save()
                assigned_count += 1
                available_slots -= 1
                students_assigned.append({
                    'id': pu.user.id,
                    'name': pu.user.get_full_name(),
                    'registration_number': pu.user.registration_number
                })
        
        # Also assign to the project owner if they are a student
        if project.user and project.user.role == 'student' and project.user.mentor != mentor:
            if available_slots > 0:
                project.user.mentor = mentor
                project.user.save()
                assigned_count += 1
                students_assigned.append({
                    'id': project.user.id,
                    'name': project.user.get_full_name(),
                    'registration_number': project.user.registration_number
                })
        
        result['message'] = f'Auto-assigned mentor {mentor.first_name} {mentor.last_name} to {assigned_count} students.'
        result['assigned_count'] = assigned_count
        result['mentor_id'] = mentor.id
        result['mentor_name'] = f"{mentor.first_name} {mentor.last_name}"
        result['students_assigned'] = students_assigned
        result['assignment_score'] = best['score']
        result['assignment_reasons'] = best['reasons']
        result['mentor_capacity'] = {
            'current': best['current_students'] + assigned_count,
            'max': best['max_students'],
            'available': available_slots
        }
        result['all_mentors_scored'] = [
            {
                'mentor_id': m['mentor'].id,
                'mentor_name': f"{m['mentor'].first_name} {m['mentor'].last_name}",
                'score': m['score'],
                'available_slots': m['available_slots'],
                'reasons': m['reasons']
            }
            for m in mentor_scores[:5]
        ]
        
        return result


# ============================================================
# ====== HELPER FUNCTION FOR KEYWORD EXTRACTION ======
# ============================================================

def extract_keywords(text):
    """
    Extract keywords from text for duplicate detection.
    """
    stop_words = {
        'the', 'a', 'an', 'of', 'for', 'on', 'at', 'to', 'in', 'with', 'by', 'from',
        'up', 'off', 'out', 'over', 'under', 'about', 'after', 'before', 'between',
        'among', 'through', 'during', 'without', 'against', 'within', 'upon', 'into',
        'and', 'or', 'but', 'nor', 'for', 'so', 'yet', 'as', 'than', 'that', 'these',
        'those', 'this', 'that', 'these', 'those', 'is', 'am', 'are', 'was', 'were',
        'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
        'would', 'shall', 'should', 'may', 'might', 'must', 'can', 'could', 'use',
        'using', 'system', 'application', 'web', 'mobile', 'project', 'development'
    }
    
    if not text:
        return []
    
    words = str(text).lower().split()
    keywords = []
    
    for word in words:
        word = ''.join(c for c in word if c.isalnum())
        if len(word) > 3 and word not in stop_words:
            keywords.append(word)
    
    return keywords


# ============================================================
# ====== PRESENTATION VIEWSET ======
# ============================================================

class PresentationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing presentation events.
    """
    queryset = Presentation.objects.all().order_by('-presentation_date', '-created_at')
    serializer_class = PresentationSerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ['presentation_date']

    def get_queryset(self):
        return self.queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated:
            raise PermissionDenied("You must be logged in to create a presentation.")
        if user.role in ['mentor', 'coordinator'] or user.is_staff:
            serializer.save()
        else:
            raise PermissionDenied("Only mentors, coordinators, or staff may create presentation events.")


# ============================================================
# ====== PRESENTATION RESULT VIEWSET ======
# ============================================================

class PresentationResultViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing student presentation results.
    """
    queryset = PresentationResult.objects.all().order_by('-presentation__presentation_date', '-created_at')
    serializer_class = PresentationResultSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['presentation', 'student', 'project']

    def get_queryset(self):
        user = self.request.user
        
        logger.info(f"PresentationResultViewSet - User: {user.id} - {user.role}")
        
        if not user.is_authenticated:
            logger.warning("User not authenticated")
            return PresentationResult.objects.none()
        
        student_id = self.request.query_params.get('student') or self.request.query_params.get('student_id')
        logger.info(f"Student ID from query: {student_id}")
        
        queryset = PresentationResult.objects.all()
        
        if student_id:
            try:
                student_id = int(student_id)
                queryset = queryset.filter(student_id=student_id)
                logger.info(f"Filtered by student_id: {student_id} - {queryset.count()} results")
                return queryset
            except (TypeError, ValueError):
                logger.warning(f"Invalid student_id: {student_id}")
        
        if user.role == 'student':
            queryset = queryset.filter(student=user)
            logger.info(f"Student {user.id} - {queryset.count()} results")
        elif user.role == 'mentor':
            queryset = queryset.filter(student__mentor=user)
            logger.info(f"Mentor {user.id} - {queryset.count()} results")
        else:
            logger.info(f"{user.role} {user.id} - {queryset.count()} results")
        
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may add presentation results.")

        student = serializer.validated_data.get('student')
        project = serializer.validated_data.get('project')
        marks = serializer.validated_data.get('marks')

        if not student and project is not None:
            student = project.user
            serializer.validated_data['student'] = student

        if student is None:
            raise PermissionDenied("A student must be specified for presentation results.")

        if user.role == 'mentor' and student.mentor_id != user.id:
            raise PermissionDenied("Mentors may only add results for their own students.")

        result = serializer.save(reviewer=user)
        
        if marks is not None:
            result.marks = marks
            result.save(update_fields=['marks'])
            logger.info(f"Presentation result created: {result.id} - Marks: {marks}")
        else:
            logger.info(f"Presentation result created: {result.id} - No marks provided")

    def perform_update(self, serializer):
        user = self.request.user
        result = self.get_object()
        if not user.is_staff and result.reviewer_id != user.id:
            raise PermissionDenied("Only the original reviewer or staff may update this result.")
        
        updated_result = serializer.save()
        marks = serializer.validated_data.get('marks')
        if marks is not None:
            updated_result.marks = marks
            updated_result.save(update_fields=['marks'])
            logger.info(f"Presentation result updated: {updated_result.id} - Marks: {marks}")

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.is_staff and instance.reviewer_id != user.id:
            raise PermissionDenied("Only the original reviewer or staff may delete this result.")
        instance.delete()

    @action(detail=True, methods=['post'])
    def calculate_total(self, request, pk=None):
        """
        Calculate and update total from criteria scores for a presentation result.
        """
        user = request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may calculate totals.")

        try:
            result = self.get_object()
            
            criteria_scores = result.criteria_scores.all()
            if not criteria_scores.exists():
                return Response({
                    'error': 'No criteria scores found for this result',
                    'id': result.id,
                    'marks': result.marks,
                    'criteria_total': result.criteria_total
                }, status=status.HTTP_200_OK)

            total_weighted_score = 0
            total_weight = 0

            for cs in criteria_scores:
                if cs.score is not None and cs.criteria.max_score > 0:
                    normalized_score = (cs.score / cs.criteria.max_score) * 100
                    weighted_score = normalized_score * cs.criteria.weight
                    total_weighted_score += weighted_score
                    total_weight += cs.criteria.weight

            if total_weight > 0:
                calculated_total = round(total_weighted_score / total_weight, 2)
                result.criteria_total = calculated_total
                result.marks = calculated_total
                result.is_graded_by_criteria = True
                result.save(update_fields=['criteria_total', 'marks', 'is_graded_by_criteria', 'updated_at'])
                
                serializer = self.get_serializer(result)
                return Response({
                    'success': True,
                    'id': result.id,
                    'marks': result.marks,
                    'criteria_total': result.criteria_total,
                    'is_graded_by_criteria': result.is_graded_by_criteria,
                    'data': serializer.data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'No valid criteria scores to calculate total',
                    'id': result.id,
                    'marks': result.marks,
                    'criteria_total': result.criteria_total
                }, status=status.HTTP_200_OK)

        except PresentationResult.DoesNotExist:
            return Response({
                'error': 'Presentation result not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error calculating total for result {pk}: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['get'])
    def criteria_scores(self, request, pk=None):
        """
        Get all criteria scores for a presentation result.
        """
        try:
            result = self.get_object()
            scores = result.criteria_scores.all()
            serializer = PresentationResultCriteriaSerializer(scores, many=True)
            return Response(serializer.data)
        except PresentationResult.DoesNotExist:
            return Response({
                'error': 'Presentation result not found'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error fetching criteria scores: {e}")
            return Response({
                'error': str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class ProjectUserViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing project-user relationships (group projects).
    """
    queryset = ProjectUser.objects.all()
    serializer_class = ProjectUserSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['project', 'user', 'role']


class DuplicateFlagViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing duplicate flags.
    - list: Get all flagged duplicates
    - retrieve: Get specific flag
    - mark_reviewed: Mark a flag as reviewed
    """
    queryset = DuplicateFlag.objects.all().order_by('-created_at')
    serializer_class = DuplicateFlagSerializer
    permission_classes = [AllowAny]
    filterset_fields = ['reviewed', 'project', 'similar_project']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return DuplicateFlag.objects.none()
        
        if user.role == 'student':
            project_ids = Project.objects.filter(
                django_models.Q(user=user) | django_models.Q(project_users__user=user)
            ).values_list('id', flat=True)
            
            queryset = queryset.filter(
                Q(project_id__in=project_ids) | Q(similar_project_id__in=project_ids)
            )
        elif user.role == 'mentor':
            student_ids = User.objects.filter(mentor_id=user.id).values_list('id', flat=True)
            project_ids = Project.objects.filter(
                Q(user_id__in=student_ids) | Q(project_users__user_id__in=student_ids)
            ).values_list('id', flat=True)
            queryset = queryset.filter(
                Q(project_id__in=project_ids) | Q(similar_project_id__in=project_ids)
            )
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def mark_reviewed(self, request, pk=None):
        duplicate_flag = self.get_object()
        duplicate_flag.reviewed = True
        duplicate_flag.reviewed_by = request.user
        duplicate_flag.save()
        serializer = self.get_serializer(duplicate_flag)
        return Response(serializer.data)


# ============================================================
# ====== CRITERIA VIEWSETS ======
# ============================================================

class PresentationCriteriaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing presentation criteria.
    """
    queryset = PresentationCriteria.objects.all()
    serializer_class = PresentationCriteriaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['presentation']

    def get_queryset(self):
        queryset = super().get_queryset()
        presentation_id = self.request.query_params.get('presentation')
        if presentation_id:
            queryset = queryset.filter(presentation_id=presentation_id)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may create presentation criteria.")
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may update presentation criteria.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may delete presentation criteria.")
        instance.delete()


class PresentationResultCriteriaViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing presentation result criteria scores.
    """
    queryset = PresentationResultCriteria.objects.all()
    serializer_class = PresentationResultCriteriaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['result', 'criteria']

    def get_queryset(self):
        queryset = super().get_queryset()
        result_id = self.request.query_params.get('result')
        criteria_id = self.request.query_params.get('criteria')
        
        if result_id:
            queryset = queryset.filter(result_id=result_id)
        if criteria_id:
            queryset = queryset.filter(criteria_id=criteria_id)
            
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may add criteria scores.")
        
        result = serializer.save()
        logger.info(f"Created criteria score: result={result.result_id}, criteria={result.criteria_id}, score={result.score}")

    def perform_update(self, serializer):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may update criteria scores.")
        
        result = serializer.save()
        logger.info(f"Updated criteria score: result={result.result_id}, criteria={result.criteria_id}, score={result.score}")

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may delete criteria scores.")
        instance.delete()

    @action(detail=False, methods=['post'], url_path='save_score')
    def save_score(self, request):
        """
        Save or update a criteria score.
        """
        user = request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may save criteria scores.")
        
        result_id = request.data.get('result')
        criteria_id = request.data.get('criteria')
        score = request.data.get('score')
        selected_option = request.data.get('selected_option', '')
        comment = request.data.get('comment', '')
        
        if not result_id or not criteria_id:
            return Response({
                'error': 'result and criteria are required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        obj, created = PresentationResultCriteria.objects.get_or_create(
            result_id=result_id,
            criteria_id=criteria_id,
            defaults={
                'score': score,
                'selected_option': selected_option,
                'comment': comment
            }
        )
        
        if not created:
            obj.score = score
            obj.selected_option = selected_option
            obj.comment = comment
            obj.save()
            logger.info(f"Updated criteria score: result={result_id}, criteria={criteria_id}, score={score}")
        else:
            logger.info(f"Created criteria score: result={result_id}, criteria={criteria_id}, score={score}")
        
        serializer = PresentationResultCriteriaSerializer(obj)
        return Response({
            'success': True,
            'created': created,
            'data': serializer.data
        }, status=status.HTTP_200_OK)


# ============================================================
# ====== AUTHENTICATION VIEWS ======
# ============================================================

@api_view(['POST'])
@csrf_exempt
def login_view(request):
    """
    Authenticate user and return user data.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response(
            {'error': 'Username and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(username=username, password=password)
    if user:
        try:
            from .serializers import UserSerializer
            Token.objects.filter(user=user).delete()
            token = Token.objects.create(user=user)
            serializer = UserSerializer(user)
            return Response({'user': serializer.data, 'token': token.key})
        except Exception as e:
            return Response({'error': str(e)}, status=500)
    
    return Response(
        {'error': 'Invalid credentials'},
        status=status.HTTP_401_UNAUTHORIZED
    )


@api_view(['POST'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def logout_view(request):
    if request.auth:
        request.auth.delete()
    return Response({'message': 'Logged out successfully'}, status=status.HTTP_200_OK)


@api_view(['GET', 'PUT'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def system_settings_view(request):
    if not request.user.is_staff and request.user.role != 'coordinator':
        raise PermissionDenied("Only coordinators or staff can manage system settings.")

    settings_obj = SystemSettings.get_solo()

    if request.method == 'GET':
        serializer = SystemSettingsSerializer(settings_obj)
        return Response(serializer.data)

    serializer = SystemSettingsSerializer(settings_obj, data=request.data, partial=True)
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)