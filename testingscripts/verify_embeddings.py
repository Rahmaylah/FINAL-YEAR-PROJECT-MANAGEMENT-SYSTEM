#!/usr/bin/env python
"""Verify embeddings in database"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fypms.settings')
django.setup()

from projects.models import Project

print("\n" + "="*70)
print("PROJECTS WITH EMBEDDINGS IN DATABASE")
print("="*70)

projects = Project.objects.filter(combined_embedding__isnull=False).order_by('-created_at')[:5]

for proj in projects:
    embedding = list(proj.combined_embedding) if proj.combined_embedding is not None else None
    print(f"\n📌 Project ID: {proj.id}")
    print(f"   Title: {proj.title}")
    print(f"   Status: {proj.status}")
    print(f"   Created: {proj.created_at}")
    if embedding:
        print(f"   ✓ Combined Embedding: {len(embedding)} dimensions")
        print(f"      First 5 values: {[f'{v:.6f}' for v in embedding[:5]]}")
        print(f"      Last 5 values: {[f'{v:.6f}' for v in embedding[-5:]]}")
    print(f"   Last similarity check: {proj.last_similarity_check}")

print("\n" + "="*70)
print(f"Total projects with embeddings: {projects.count()}")
print("="*70 + "\n")
