#!/usr/bin/env python3
import os
import sys
import django
from django.conf import settings

# Add the project directory to the Python path
sys.path.insert(0, '/home/revocajana/projects/fypms')

# Configure Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fypms.settings')
django.setup()

from accounts.models import User
from projects.models import Project, ProjectUser
from django.test import RequestFactory
from api.views import ProjectViewSet

def test_api_filtering():
    print("=== Testing API Filtering ===")

    # Get all users
    users = User.objects.all()
    print(f"Total users: {users.count()}")

    for user in users:
        print(f"\nUser: {user.username} (Role: {user.role})")

        # Create a mock request
        factory = RequestFactory()
        request = factory.get('/api/projects/')
        request.user = user

        # Create viewset instance
        viewset = ProjectViewSet()
        viewset.request = request

        # Get queryset
        queryset = viewset.get_queryset()
        projects = list(queryset)

        print(f"  Projects visible: {len(projects)}")
        for project in projects:
            print(f"    - {project.title} (Creator: {project.user.username})")

    print("\n=== ProjectUser Relationships ===")
    for pu in ProjectUser.objects.all():
        print(f"Project: {pu.project.title} -> User: {pu.user.username} (Role: {pu.role})")

if __name__ == '__main__':
    test_api_filtering()