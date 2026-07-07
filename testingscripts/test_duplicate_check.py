#!/usr/bin/env python
"""
Test script for duplicate check API endpoint
"""
import os
import sys
import django
from pathlib import Path

# Setup Django
sys.path.insert(0, str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fypms.settings')
django.setup()

import requests
from projects.models import Project
from projects.similarity import get_similarity_scorer

def test_duplicate_check():
    """Test the duplicate check functionality"""
    print("=== Testing Duplicate Check API ===")

    # Get a project to test with
    try:
        project = Project.objects.filter(title__icontains='AI').first()
        if not project:
            print("No AI projects found, creating test project...")
            # Create a test project
            from accounts.models import User
            user = User.objects.filter(role='student').first()
            if not user:
                print("No users found, skipping test")
                return

            project = Project.objects.create(
                title="AI Chatbot for Customer Service",
                main_objective="Develop an AI-powered chatbot",
                specific_objectives="Implement NLP, integrate with APIs",
                project_description="A comprehensive chatbot system",
                user=user
            )
            print(f"Created test project: {project.title}")

        print(f"Testing duplicate check for project: {project.title}")
        print(f"Project ID: {project.id}")

        # Test the similarity scorer directly
        scorer = get_similarity_scorer()
        similar = scorer.find_similar_projects(
            project_id=project.id,
            title=project.title,
            objectives=f"{project.main_objective} {project.specific_objectives}",
            title_embedding=project.title_embedding,
            objectives_embedding=project.objectives_embedding,
            combined_embedding=project.combined_embedding,
            limit=5
        )

        print(f"Found {len(similar)} similar projects:")
        for sim in similar:
            print(f"  - {sim['title'][:50]}... (similarity: {sim['hybrid_similarity']:.3f})")

        # Test API endpoint (if server is running)
        try:
            response = requests.post(
                f'http://localhost:8000/api/projects/{project.id}/duplicate_check/',
                timeout=5
            )
            if response.status_code == 200:
                data = response.json()
                print(f"API Response: {data}")
            else:
                print(f"API returned status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"API test failed (server not running?): {e}")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    test_duplicate_check()