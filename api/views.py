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
        
        # Student anaona projects zake TU (sio za wengine)
        if user.role == 'student':
            return Project.objects.filter(
                django_models.Q(user=user) | 
                django_models.Q(project_users__user=user)
            ).distinct().order_by('-created_at')
        
        # Mentor, coordinator wanaona zote
        return Project.objects.all().order_by('-created_at')
    
    def get_object(self):
        obj = super().get_object()
        user = self.request.user

        if not user.is_authenticated:
            raise PermissionDenied("Authentication required.")
        
        # Superuser au staff wanaona zote
        if user.is_superuser or user.is_staff:
            return obj
        
        # Student anaweza kuona project yake TU
        if user.role == 'student':
            if ProjectUser.objects.filter(project=obj, user=user).exists() or obj.user_id == user.id:
                return obj
            raise PermissionDenied("You do not have permission to access this project.")
        
        # Mentor, coordinator wanaona zote
        return obj
    
    # ============================================================
    # ====== PERFORM_CREATE - AUTO DUPLICATE CHECK ======
    # ============================================================
    def perform_create(self, serializer):
        """Create project and automatically check for duplicates"""
        # ====== STEP 1: Save project first ======
        project = serializer.save(user=self.request.user)
        logger.info(f"📌 Project {project.id} created: {project.title}")

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
        mentor_allowed_fields = {'status', 'mentor_comment'}
        
        # ============================================================
        # ====== IF MENTOR IS UPDATING, SKIP DUPLICATE CHECK ======
        # ============================================================
        if is_mentor and updated_fields.issubset(mentor_allowed_fields):
            # ====== CRITICAL: Get original project state BEFORE saving ======
            original_project = Project.objects.get(id=project.id)
            original_flagged = original_project.is_flagged_duplicate
            original_score = original_project.duplicate_check_score
            
            logger.info(f"🔍 Original project {original_project.id}: flagged={original_flagged}, score={original_score}")
            
            # ====== SAVE PROJECT ======
            updated_project = serializer.save()
            logger.info(f"🔄 Mentor update for project {updated_project.id}: {updated_fields}")
            
            # ====== FORCE RESET TO ORIGINAL FLAG STATE ======
            if not original_flagged:
                # Was UNFLAGGED - keep UNFLAGGED
                Project.objects.filter(id=updated_project.id).update(
                    is_flagged_duplicate=False,
                    duplicate_check_score=None,
                    duplicate_keywords_matched=[]
                )
                DuplicateFlag.objects.filter(project=updated_project).delete()
                DuplicateFlag.objects.filter(similar_project=updated_project).delete()
                logger.info(f"✅ FORCED project {updated_project.id} to remain UNFLAGGED")
            else:
                # Was FLAGGED - keep FLAGGED
                Project.objects.filter(id=updated_project.id).update(
                    is_flagged_duplicate=True,
                    duplicate_check_score=original_score
                )
                logger.info(f"✅ FORCED project {updated_project.id} to remain FLAGGED with score {original_score}")
            
            # Update instance
            updated_project.is_flagged_duplicate = original_flagged
            updated_project.duplicate_check_score = original_score
            
            return

        # ============================================================
        # ====== NORMAL UPDATE (NOT MENTOR) ======
        # ============================================================
        
        # ====== STEP 1: Save updated project ======
        updated_project = serializer.save()
        logger.info(f"🔄 Project {updated_project.id} updated: {updated_project.title}")

        # ====== STEP 2: Regenerate embeddings if content changed ======
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
                logger.info(f"✅ Regenerated embeddings for project {updated_project.id}")
            else:
                logger.warning(f"❌ Failed to regenerate embeddings for project {updated_project.id}")

        # ====== STEP 3: Run duplicate check ONLY if content changed ======
        if content_changed:
            self._run_duplicate_check(updated_project)
        else:
            logger.info(f"⏭️ No content changes - skipping duplicate check for project {updated_project.id}")
    # def perform_update(self, serializer):
    #     """Update project and automatically re-check for duplicates"""
    #     # Get the existing project instance
    #     project = self.get_object()
        
    #     # ====== STEP 1: Save updated project ======
    #     updated_project = serializer.save()
    #     logger.info(f"🔄 Project {updated_project.id} updated: {updated_project.title}")

    #     # ====== STEP 2: Regenerate embeddings if content changed ======
    #     # Check if important fields changed
    #     fields_to_check = ['title', 'main_objective', 'project_description', 'specific_objectives']
    #     content_changed = False
        
    #     for field in fields_to_check:
    #         old_value = getattr(project, field)
    #         new_value = getattr(updated_project, field)
    #         if old_value != new_value:
    #             content_changed = True
    #             break
        
    #     if content_changed:
    #         from projects.utils import generate_project_embeddings
    #         embeddings = generate_project_embeddings(
    #             title=updated_project.title,
    #             objectives=updated_project.main_objective,
    #             description=updated_project.project_description
    #         )
            
    #         if embeddings:
    #             updated_project.title_embedding = embeddings.get('title_embedding')
    #             updated_project.objectives_embedding = embeddings.get('objectives_embedding')
    #             updated_project.combined_embedding = embeddings.get('combined_embedding')
    #             updated_project.last_similarity_check = timezone.now()
    #             updated_project.save(update_fields=[
    #                 'title_embedding', 'objectives_embedding', 
    #                 'combined_embedding', 'last_similarity_check'
    #             ])
    #             logger.info(f"✅ Regenerated embeddings for project {updated_project.id}")
    #         else:
    #             logger.warning(f"❌ Failed to regenerate embeddings for project {updated_project.id}")

    #     # ====== STEP 3: Run duplicate check ======
    #     self._run_duplicate_check(updated_project)

    # ============================================================
    # ====== COMMON DUPLICATE CHECK FUNCTION ======
    # ============================================================
    def _run_duplicate_check(self, project):
        """
        Common function to run duplicate check for a project.
        Used by both create and update operations.
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
                    logger.info(f"✅ Generated embeddings for project {project.id}")
                else:
                    logger.warning(f"❌ Failed to generate embeddings for project {project.id}")
                    return

            # ====== STEP 2: Get settings ======
            settings = SystemSettings.get_solo()
            auto_flag_threshold = settings.duplicate_auto_flag_threshold or 0.5

            # ====== STEP 3: Find similar projects using pgvector ======
            try:
                from pgvector.django import CosineDistance
                
                similar_projects = Project.objects.exclude(id=project.id).exclude(
                    combined_embedding__isnull=True
                ).annotate(
                    distance=CosineDistance('combined_embedding', project.combined_embedding)
                ).filter(
                    distance__lt=1 - 0.3  # Threshold ya kuangalia
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

            # ====== STEP 5: Keyword matching for better accuracy ======
            if best_match and max_similarity >= 0.3:
                text1 = f"{project.title} {project.main_objective} {project.project_description or ''}"
                text2 = f"{best_match.title} {best_match.main_objective} {best_match.project_description or ''}"
                keywords1 = set(extract_keywords(text1))
                keywords2 = set(extract_keywords(text2))
                common = keywords1.intersection(keywords2)
                matched_keywords = list(common)[:10]

            # ====== STEP 6: Flag if duplicate found ======
            if best_match and max_similarity >= auto_flag_threshold:
                # Create or update duplicate flag
                flag, created = DuplicateFlag.objects.get_or_create(
                    project=project,
                    similar_project=best_match,
                    defaults={
                        'similarity_score': max_similarity,
                    }
                )
                
                if not created:
                    flag.similarity_score = max_similarity
                    flag.save()
                
                # ====== FLAG CURRENT PROJECT ======
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
                
                # ====== ALSO FLAG THE SIMILAR PROJECT (BOTH SIDES) ======
                try:
                    similar_project = Project.objects.get(id=best_match.id)
                    if not similar_project.is_flagged_duplicate:
                        flag2, created2 = DuplicateFlag.objects.get_or_create(
                            project=similar_project,
                            similar_project_id=project.id,
                            defaults={
                                'similarity_score': max_similarity,
                            }
                        )
                        if created2:
                            similar_project.is_flagged_duplicate = True
                            similar_project.duplicate_check_score = max_similarity
                            similar_project.save(update_fields=[
                                'is_flagged_duplicate', 'duplicate_check_score'
                            ])
                            logger.info(f"✅ Also flagged similar project {similar_project.id}")
                except Project.DoesNotExist:
                    pass
                
                logger.info(f"🚨 Project {project.id} FLAGGED! Score: {max_similarity:.3f}")
                
            else:
                # ====== HAKUNA DUPLICATE - RESET FLAG ======
                project.is_flagged_duplicate = False
                project.duplicate_check_score = max_similarity if max_similarity > 0 else None
                project.duplicate_keywords_matched = matched_keywords if matched_keywords else []
                project.last_similarity_check = timezone.now()
                
                Project.objects.filter(id=project.id).update(
                    is_flagged_duplicate=False,
                    duplicate_check_score=project.duplicate_check_score,
                    duplicate_keywords_matched=project.duplicate_keywords_matched,
                    last_similarity_check=timezone.now()
                )
                
                # Delete existing flags for this project
                DuplicateFlag.objects.filter(project=project).delete()
                
                if max_similarity > 0:
                    logger.info(f"📊 Project {project.id} similarity: {max_similarity:.3f} (below threshold)")
                else:
                    logger.info(f"✅ Project {project.id} no duplicates found")

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
        (Hii ni kwa ajili ya button ya "Check Duplicates" - bado inabaki)
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
        This endpoint is used by the Student Dashboard to show related projects.
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
    # ====== GET ALL SIMILAR PROJECTS (BOTH SIDES) - UNIQUE ======
    # ============================================================
    @action(detail=True, methods=['get'], url_path='similar-all')
    def similar_all(self, request, pk=None):
        """
        Get ALL similar projects for a given project.
        Hii inarudisha projects zote ambazo zimefanana na project hii
        kutoka pande zote mbili za DuplicateFlag.
        
        ====== FIX: Inaondoa duplicates ======
        """
        try:
            project = self.get_object()
            
            # Get all duplicate flags for this project (both sides)
            flags = DuplicateFlag.objects.filter(
                Q(project=project) | Q(similar_project=project)
            ).select_related('project', 'similar_project', 'project__user', 'similar_project__user')
            
            if not flags.exists():
                return Response({
                    'count': 0,
                    'results': [],
                    'project_id': project.id,
                    'message': 'No similar projects found'
                })
            
            # ====== USE SET TO AVOID DUPLICATES ======
            seen_project_ids = set()
            similar_projects_data = []
            
            for flag in flags:
                # Determine which project is the "other" one
                if flag.project.id == project.id:
                    other_project = flag.similar_project
                else:
                    other_project = flag.project
                
                # ====== SKIP IF ALREADY SEEN ======
                if other_project.id in seen_project_ids:
                    continue
                seen_project_ids.add(other_project.id)
                
                # Get author name
                author_name = "Unknown"
                if other_project.user:
                    name_parts = [
                        other_project.user.first_name or '',
                        other_project.user.middle_name or '',
                        other_project.user.last_name or ''
                    ]
                    author_name = ' '.join(filter(None, name_parts)).strip() or other_project.user.username or "Unknown"
                
                # Get mentor name
                mentor_name = "N/A"
                if other_project.user and other_project.user.mentor:
                    mentor = other_project.user.mentor
                    name_parts = [
                        mentor.first_name or '',
                        mentor.middle_name or '',
                        mentor.last_name or ''
                    ]
                    mentor_name = ' '.join(filter(None, name_parts)).strip() or mentor.username or "N/A"
                
                # Get mentor comment
                mentor_comment = other_project.mentor_comment if other_project.mentor_comment else None
                
                # Get project type name
                project_type_name = "N/A"
                if other_project.project_type:
                    project_type_name = other_project.project_type.name
                
                # ====== GET REGISTRATION NUMBERS ======
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
            
            # Sort by similarity score (highest first)
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
        Falls back to basic search if scikit-learn is not installed.
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
# ====== HELPER FUNCTION FOR KEYWORD EXTRACTION ======
# ============================================================

def extract_keywords(text):
    """
    Extract keywords from text for duplicate detection.
    Removes stop words and common words.
    """
    # Common stop words
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
    
    # Split and clean
    words = str(text).lower().split()
    keywords = []
    
    for word in words:
        # Remove punctuation
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
        
        # ====== Check authentication ======
        if not user.is_authenticated:
            return self.queryset.none()
        
        # ====== Get student_id from query params ======
        student_id = self.request.query_params.get('student')
        
        queryset = self.queryset.all()
        
        # ====== Filter by student_id if provided ======
        if student_id:
            try:
                student_id = int(student_id)
                queryset = queryset.filter(student_id=student_id)
                return queryset
            except (TypeError, ValueError):
                pass
        
        # ====== Role-based filtering ======
        if user.role == 'student':
            queryset = queryset.filter(student=user)
        elif user.role == 'mentor':
            queryset = queryset.filter(student__mentor=user)
        
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may add presentation results.")

        student = serializer.validated_data.get('student')
        project = serializer.validated_data.get('project')

        if not student and project is not None:
            student = project.user
            serializer.validated_data['student'] = student

        if student is None:
            raise PermissionDenied("A student must be specified for presentation results.")

        if user.role == 'mentor' and student.mentor_id != user.id:
            raise PermissionDenied("Mentors may only add results for their own students.")

        serializer.save(reviewer=user)

    def perform_update(self, serializer):
        user = self.request.user
        result = self.get_object()
        if not user.is_staff and result.reviewer_id != user.id:
            raise PermissionDenied("Only the original reviewer or staff may update this result.")
        serializer.save()

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
        """
        Override to filter flags based on user permissions.
        Students can only see flags for their own projects.
        """
        queryset = super().get_queryset()
        user = self.request.user
        
        if not user.is_authenticated:
            return DuplicateFlag.objects.none()
        
        if user.role == 'student':
            # Student can only see flags for their own projects
            # Get all project IDs that belong to this student
            project_ids = Project.objects.filter(
                django_models.Q(user=user) | django_models.Q(project_users__user=user)
            ).values_list('id', flat=True)
            
            # Filter flags where project OR similar_project belongs to student
            queryset = queryset.filter(
                Q(project_id__in=project_ids) | Q(similar_project_id__in=project_ids)
            )
        elif user.role == 'mentor':
            # Mentor can see flags for their students' projects
            student_ids = User.objects.filter(mentor_id=user.id).values_list('id', flat=True)
            project_ids = Project.objects.filter(
                Q(user_id__in=student_ids) | Q(project_users__user_id__in=student_ids)
            ).values_list('id', flat=True)
            queryset = queryset.filter(
                Q(project_id__in=project_ids) | Q(similar_project_id__in=project_ids)
            )
        # Coordinator and staff can see all flags
        
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
    
    - list: Get all criteria (filter by presentation)
    - retrieve: Get specific criteria
    - create: Create new criteria
    - update: Update criteria
    - delete: Delete criteria
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
    
    - list: Get all criteria scores (filter by result)
    - retrieve: Get specific criteria score
    - create: Create new criteria score
    - update: Update criteria score
    - delete: Delete criteria score
    - save_score: Save or update a criteria score (create if not exists)
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
        logger.info(f"✅ Created criteria score: result={result.result_id}, criteria={result.criteria_id}, score={result.score}")

    def perform_update(self, serializer):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may update criteria scores.")
        
        result = serializer.save()
        logger.info(f"✅ Updated criteria score: result={result.result_id}, criteria={result.criteria_id}, score={result.score}")

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may delete criteria scores.")
        instance.delete()

    # ============================================================
    # ====== FIX: CUSTOM ACTION TO SAVE OR CREATE SCORE ======
    # ============================================================
    @action(detail=False, methods=['post'], url_path='save_score')
    def save_score(self, request):
        """
        Save or update a criteria score.
        If it exists, update it. If not, create it.
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
        
        # ====== Try to get existing, or create new ======
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
            # Update existing
            obj.score = score
            obj.selected_option = selected_option
            obj.comment = comment
            obj.save()
            logger.info(f"✅ Updated criteria score: result={result_id}, criteria={criteria_id}, score={score}")
        else:
            logger.info(f"✅ Created criteria score: result={result_id}, criteria={criteria_id}, score={score}")
        
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
    # Fix: Use request.user instead of user
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