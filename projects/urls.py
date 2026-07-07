from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, ProjectViewSet, ProjectTypeViewSet, ProjectUserViewSet,
    DuplicateFlagViewSet, PresentationViewSet, PresentationResultViewSet,
    PresentationCriteriaViewSet, PresentationResultCriteriaViewSet,
    login_view, logout_view, system_settings_view
)

router = DefaultRouter()
router.register(r'users', UserViewSet, basename='user')
router.register(r'projects', ProjectViewSet, basename='project')
router.register(r'project-types', ProjectTypeViewSet, basename='projecttype')
router.register(r'project-users', ProjectUserViewSet, basename='projectuser')
router.register(r'presentations', PresentationViewSet, basename='presentation')
router.register(r'presentation-results', PresentationResultViewSet, basename='presentationresult')
router.register(r'presentation-reviews', PresentationResultViewSet, basename='presentationreview')
router.register(r'duplicate-flags', DuplicateFlagViewSet, basename='duplicateflag')
# NEW: Presentation Criteria endpoints
router.register(r'presentation-criteria', PresentationCriteriaViewSet, basename='presentationcriteria')
router.register(r'presentation-result-criteria', PresentationResultCriteriaViewSet, basename='presentationresultcriteria')

app_name = 'api'

urlpatterns = [
    path('', include(router.urls)),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('settings/', system_settings_view, name='system-settings'),
]