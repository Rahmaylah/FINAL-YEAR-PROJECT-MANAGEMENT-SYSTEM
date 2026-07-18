# api/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from django.views.decorators.csrf import csrf_exempt
from .views import (
    UserViewSet, ProjectViewSet, ProjectTypeViewSet, ProjectUserViewSet,
    DuplicateFlagViewSet, PresentationViewSet, PresentationResultViewSet,
    PresentationCriteriaViewSet, PresentationResultCriteriaViewSet,
    login_view, logout_view, system_settings_view
)

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from accounts.models import User


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_mentors_view(request):
    """Get mentors available for assignment based on capacity."""
    mentors = User.objects.filter(role='mentor')
    
    available_mentors = []
    
    for mentor in mentors:
        current_students = User.objects.filter(mentor=mentor, role='student').count()
        max_students = mentor.max_students or 5
        available_slots = max_students - current_students
        
        if available_slots <= 0:
            continue
        
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
        })
    
    available_mentors.sort(key=lambda x: x['available_slots'], reverse=True)
    
    return Response({
        'mentors': available_mentors,
        'total': len(available_mentors)
    })


# ====== BULK ACTION VIEW ======
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@csrf_exempt
def bulk_action_view(request):
    """
    Perform bulk actions on multiple projects.
    """
    from projects.models import Project, ProjectUser
    from accounts.models import User
    from rest_framework.exceptions import PermissionDenied
    
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
            status=400
        )
    
    if not project_ids:
        return Response(
            {'error': 'No projects selected. Please provide project_ids.'},
            status=400
        )
    
    # Get projects
    projects = Project.objects.filter(id__in=project_ids)
    
    if not projects.exists():
        return Response(
            {'error': 'No valid projects found with the provided IDs.'},
            status=404
        )
    
    # Perform action
    results = []
    errors = []
    processed_count = 0
    
    for project in projects:
        try:
            result = _process_bulk_action(project, action, data, user)
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
    }, status=200)


def _process_bulk_action(project, action, data, user):
    """Process a single bulk action for a project."""
    from projects.models import ProjectUser
    from accounts.models import User
    
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
        result = _auto_assign_mentor_to_project(project)
        
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


def _auto_assign_mentor_to_project(project):
    """
    Auto-assign the best mentor to a project based on:
    1. Specialization match
    2. Available capacity
    3. Current load balancing
    """
    from accounts.models import User
    from projects.models import ProjectUser
    
    result = {
        'id': project.id,
        'title': project.title,
        'status': 'success'
    }
    
    project_type = project.project_type
    mentors = User.objects.filter(role='mentor')
    
    if not mentors.exists():
        raise ValueError('No mentors available in the system.')
    
    mentor_scores = []
    
    for mentor in mentors:
        current_students = User.objects.filter(mentor=mentor, role='student').count()
        max_students = mentor.max_students or 5
        available_slots = max_students - current_students
        
        if available_slots <= 0:
            continue
        
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
    
    mentor_scores.sort(key=lambda x: x['score'], reverse=True)
    
    best = mentor_scores[0]
    mentor = best['mentor']
    available_slots = best['available_slots']
    
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


router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'project-types', ProjectTypeViewSet, basename='projecttype')
router.register(r'project-users', ProjectUserViewSet, basename='projectuser')
router.register(r'presentations', PresentationViewSet, basename='presentation')
router.register(r'presentation-results', PresentationResultViewSet, basename='presentationresult')
router.register(r'presentation-reviews', PresentationResultViewSet, basename='presentationreview')
router.register(r'duplicate-flags', DuplicateFlagViewSet, basename='duplicateflag')
router.register(r'presentation-criteria', PresentationCriteriaViewSet, basename='presentationcriteria')
router.register(r'presentation-result-criteria', PresentationResultCriteriaViewSet, basename='presentationresultcriteria')

app_name = 'api'

urlpatterns = [
    # ====== MANUAL ENDPOINTS (MUST BE BEFORE ROUTER) ======
    path('projects/bulk_action/', bulk_action_view, name='bulk_action'),
    path('projects/available_mentors/', available_mentors_view, name='available_mentors'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('settings/', system_settings_view, name='system-settings'),
    # ====== ROUTER ======
    path('', include(router.urls)),
]