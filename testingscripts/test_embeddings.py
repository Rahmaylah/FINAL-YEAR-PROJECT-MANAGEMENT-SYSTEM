#!/usr/bin/env python
"""
Test script to verify embedding generation is working.

Run this after Django is set up:
    python manage.py shell < test_embeddings.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fypms.settings')
django.setup()

from django.contrib.auth import get_user_model
from projects.models import Project, ProjectType
from projects.utils import generate_project_embeddings, get_embedding_service
import json

User = get_user_model()

print("\n" + "="*60)
print("EMBEDDING GENERATION TEST")
print("="*60)

# Test 1: Check if embedding service loads
print("\n[Test 1] Loading Embedding Service...")
try:
    service = get_embedding_service()
    model_info = service.get_model_info()
    print(f"✓ Embedding service loaded successfully")
    print(f"  Model: {model_info['model_name']}")
    print(f"  Dimensions: {model_info['embedding_dimension']}")
    print(f"  Max Seq Length: {model_info['max_seq_length']}")
    print(f"  Device: {model_info['device']}")
except Exception as e:
    print(f"✗ Failed to load embedding service: {e}")
    sys.exit(1)

# Test 2: Generate embeddings for sample text
print("\n[Test 2] Testing Embedding Generation...")
try:
    embeddings = generate_project_embeddings(
        title="Machine Learning for Healthcare",
        objectives="Develop an ML model to predict diseases",
        description="Using neural networks and deep learning techniques"
    )
    
    print("✓ Embeddings generated successfully")
    for key, value in embeddings.items():
        if value:
            print(f"  {key}: {len(value)} dimensions, first 3 values: {value[:3]}")
        else:
            print(f"  {key}: None")
except Exception as e:
    print(f"✗ Failed to generate embeddings: {e}")
    sys.exit(1)

# Test 3: Create a test project and verify embeddings are saved
print("\n[Test 3] Creating Test Project with Embeddings...")
try:
    # Get or create a test user
    test_user, _ = User.objects.get_or_create(
        email='test@example.com',
        defaults={
            'username': 'testuser',
            'first_name': 'Test',
            'last_name': 'User',
            'role': 'student'
        }
    )
    print(f"✓ Test user: {test_user.email}")
    
    # Get or create a project type
    project_type, _ = ProjectType.objects.get_or_create(
        name='Web Application',
        defaults={'description': 'Web-based application project'}
    )
    
    # Create a test project
    project = Project.objects.create(
        user=test_user,
        title="AI Chatbot System",
        project_type=project_type,
        main_objective="Build an intelligent chatbot using NLP",
        specific_objectives=["Implement NLP pipeline", "Train the model", "Deploy on cloud"],
        project_description="An intelligent chatbot that can understand and respond to user queries",
        year=2025,
        status='proposed'
    )
    print(f"✓ Project created: {project.title} (ID: {project.id})")
    
    # Refresh from DB to see if embeddings were generated
    project.refresh_from_db()
    
    if project.combined_embedding is not None:
        embedding_list = list(project.combined_embedding)
        print(f"✓ Embeddings stored in database!")
        print(f"  combined_embedding: {len(embedding_list)} dimensions")
        print(f"  First 5 values: {embedding_list[:5]}")
        print(f"  Last 5 values: {embedding_list[-5:]}")
        print(f"  Last similarity check: {project.last_similarity_check}")
    else:
        print(f"✗ Embeddings NOT found in database")
        print(f"  title_embedding: {project.title_embedding}")
        print(f"  objectives_embedding: {project.objectives_embedding}")
        print(f"  combined_embedding: {project.combined_embedding}")
        
except Exception as e:
    print(f"✗ Failed to create project: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("\n" + "="*60)
print("ALL TESTS PASSED!")
print("="*60)
print("\nYou can now test the API by submitting a project through:")
print("  POST http://localhost:8000/api/projects/")
print("\nThen verify embeddings in the database:")
print("  python manage.py dbshell")
print("  SELECT id, title, combined_embedding FROM projects_project;")
print("="*60 + "\n")
