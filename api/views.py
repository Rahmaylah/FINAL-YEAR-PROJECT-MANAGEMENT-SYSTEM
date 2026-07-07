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
from django.db import models

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
    - create: Submit new project
    - update: Update project (owner or admin)
    - destroy: Delete project (owner or admin)
    - duplicate_check: Manually trigger duplicate detection for a project
    - similar: Get similar projects with mentor comments (NEW)
    """
    queryset = Project.objects.all().order_by('-created_at')
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    filterset_fields = ['project_type', 'year', 'status', 'is_flagged_duplicate']
    search_fields = ['title', 'main_objective', 'specific_objectives', 'project_description']
    
    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Project.objects.all().order_by('-created_at')
        if user.role == 'student':
            # Student can see their own projects AND projects that are flagged as duplicates
            return Project.objects.filter(
                models.Q(user=user) | 
                models.Q(project_users__user=user) |
                models.Q(is_flagged_duplicate=True)  # Allow students to see flagged projects
            ).distinct().order_by('-created_at')
        else:
            return Project.objects.all().order_by('-created_at')
    
    def get_object(self):
        obj = super().get_object()
        user = self.request.user

        # Allow access if user is not a student, or if project belongs to user, or if project is flagged as duplicate
        if not user.is_authenticated or user.role != 'student':
            return obj
        
        # Student can access if they own the project, are a member, or the project is flagged as duplicate
        if ProjectUser.objects.filter(project=obj, user=user).exists() or obj.user_id == user.id or obj.is_flagged_duplicate:
            return obj

        raise PermissionDenied("You do not have permission to access this project.")
    
    def perform_create(self, serializer):
        project = serializer.save(user=self.request.user)

        try:
            scorer = get_similarity_scorer()
            
            # Use safe_to_list for all embeddings
            title_emb = safe_to_list(project.title_embedding)
            obj_emb = safe_to_list(project.objectives_embedding)
            combined_emb = safe_to_list(project.combined_embedding)
            
            similar_projects = scorer.find_similar_projects(
                project_id=project.id,
                title=project.title,
                objectives=f"{project.main_objective} {project.specific_objectives}",
                title_embedding=title_emb,
                objectives_embedding=obj_emb,
                combined_embedding=combined_emb,
                limit=5
            )

            for similar in similar_projects:
                if similar['auto_flag']:
                    DuplicateFlag.objects.create(
                        project=project,
                        similar_project_id=similar['id'],
                        similarity_score=similar['hybrid_similarity'],
                        flagged_by=None
                    )
                    project.is_flagged_duplicate = True
                    project.duplicate_check_score = similar['hybrid_similarity']
                    project.save(update_fields=['is_flagged_duplicate', 'duplicate_check_score'])
                    break

        except Exception as e:
            logger.error(f"Failed to auto-check duplicates for project {project.id}: {e}")
        
    @action(detail=True, methods=['post'])
    def duplicate_check(self, request, pk=None):
        """
        Manually trigger duplicate detection for a project.
        Generates embeddings if they don't exist, then checks for similar projects.
        """
        try:
            project = self.get_object()
            
            # Generate embeddings if they don't exist
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
                    project.save()
                    logger.info(f"✅ Generated embeddings for project {project.id} during duplicate check")
                else:
                    return Response({
                        'error': 'Failed to generate embeddings for this project',
                        'project_id': project.id
                    }, status=status.HTTP_400_BAD_REQUEST)
            
            # Get similarity scorer
            scorer = get_similarity_scorer()
            
            # Convert embeddings to lists using safe_to_list
            title_emb = safe_to_list(project.title_embedding)
            obj_emb = safe_to_list(project.objectives_embedding)
            combined_emb = safe_to_list(project.combined_embedding)
            
            if combined_emb is None:
                return Response({
                    'error': 'No combined embedding available for this project',
                    'project_id': project.id
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Find similar projects
            similar_projects = scorer.find_similar_projects(
                project_id=project.id,
                title=project.title,
                objectives=f"{project.main_objective} {project.specific_objectives}",
                title_embedding=title_emb,
                objectives_embedding=obj_emb,
                combined_embedding=combined_emb,
                limit=10
            )
            
            # Create duplicate flags for auto-flagged projects
            auto_flagged = []
            for similar in similar_projects:
                if similar.get('auto_flag', False):
                    flag, created = DuplicateFlag.objects.get_or_create(
                        project=project,
                        similar_project_id=similar['id'],
                        defaults={
                            'similarity_score': similar['hybrid_similarity'],
                        }
                    )
                    if created:
                        auto_flagged.append(similar)
            
            # Update project status
            if auto_flagged:
                project.is_flagged_duplicate = True
                project.save(update_fields=['is_flagged_duplicate'])
            
            if similar_projects:
                max_similarity = max(s['hybrid_similarity'] for s in similar_projects)
                project.duplicate_check_score = max_similarity
                project.save(update_fields=['duplicate_check_score'])
            
            project.last_similarity_check = timezone.now()
            project.save(update_fields=['last_similarity_check'])
            
            return Response({
                'project_id': project.id,
                'project_title': project.title,
                'similar_projects': similar_projects,
                'auto_flagged_count': len(auto_flagged),
                'total_similar': len(similar_projects),
                'is_flagged': project.is_flagged_duplicate
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
        
        scorer = get_similarity_scorer()
        results = []
        total_auto_flagged = 0
        
        for project in projects:
            try:
                # Generate embeddings if needed
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
                        project.save()
                
                title_emb = safe_to_list(project.title_embedding)
                obj_emb = safe_to_list(project.objectives_embedding)
                combined_emb = safe_to_list(project.combined_embedding)

                similar_projects = scorer.find_similar_projects(
                    project_id=project.id,
                    title=project.title,
                    objectives=f"{project.main_objective} {project.specific_objectives}",
                    title_embedding=title_emb,
                    objectives_embedding=obj_emb,
                    combined_embedding=combined_emb,
                    limit=5
                )
                
                auto_flagged = 0
                for similar in similar_projects:
                    if similar.get('auto_flag', False):
                        flag, created = DuplicateFlag.objects.get_or_create(
                            project=project,
                            similar_project_id=similar['id'],
                            defaults={
                                'similarity_score': similar['hybrid_similarity'],
                            }
                        )
                        if created:
                            auto_flagged += 1
                            total_auto_flagged += 1
                            project.is_flagged_duplicate = True
                            project.save(update_fields=['is_flagged_duplicate'])
                
                if similar_projects:
                    max_similarity = max(s['hybrid_similarity'] for s in similar_projects)
                    project.duplicate_check_score = max_similarity
                    project.save(update_fields=['duplicate_check_score'])
                
                project.last_similarity_check = timezone.now()
                project.save(update_fields=['last_similarity_check'])
                
                results.append({
                    'project_id': project.id,
                    'project_title': project.title,
                    'similar_projects_found': len(similar_projects),
                    'auto_flagged': auto_flagged,
                    'processed': True
                })
                
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
    # NEW ACTION: Get similar projects with mentor comments
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
    # Alternative: Similar projects with advanced search
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
        if not user.is_authenticated:
            return self.queryset.none()
        if user.role == 'student':
            return self.queryset.filter(student=user)
        if user.role == 'mentor':
            return self.queryset.filter(student__mentor=user)
        return self.queryset

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
    """
    queryset = PresentationResultCriteria.objects.all()
    serializer_class = PresentationResultCriteriaSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]
    filterset_fields = ['result', 'criteria']

    def get_queryset(self):
        queryset = super().get_queryset()
        result_id = self.request.query_params.get('result')
        if result_id:
            queryset = queryset.filter(result_id=result_id)
        return queryset

    def perform_create(self, serializer):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may add criteria scores.")
        serializer.save()

    def perform_update(self, serializer):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may update criteria scores.")
        serializer.save()

    def perform_destroy(self, instance):
        user = self.request.user
        if not user.is_authenticated or (not user.is_staff and user.role not in ['mentor', 'coordinator']):
            raise PermissionDenied("Only mentors, coordinators, or staff may delete criteria scores.")
        instance.delete()


# ============================================================
# END CRITERIA VIEWSETS
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