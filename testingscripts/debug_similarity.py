"""
Debug script to find similar projects and calculate their scores manually.

Usage:
    python manage.py shell < debug_similarity.py
"""

from projects.models import Project, DuplicateFlag
from projects.similarity import get_similarity_scorer
import sys

scorer = get_similarity_scorer()

print("=" * 80)
print("DUPLICATE DETECTION DEBUGGING")
print("=" * 80)

# Get all projects
projects = Project.objects.all()
print(f"\nTotal projects: {projects.count()}\n")

# Check embeddings
projects_with_embeddings = projects.filter(combined_embedding__isnull=False)
projects_without_embeddings = projects.filter(combined_embedding__isnull=True)

print(f"Projects with embeddings: {projects_with_embeddings.count()}")
print(f"Projects without embeddings: {projects_without_embeddings.count()}\n")

if projects_without_embeddings.exists():
    print("⚠️  Projects WITHOUT embeddings:")
    for p in projects_without_embeddings[:5]:
        print(f"   - {p.id}: {p.title}")
    print()

# Check similarity threshold
print(f"Similarity threshold: {scorer.similarity_threshold}")
print(f"Auto-flag threshold: {scorer.auto_flag_threshold}")
print(f"Semantic weight: {scorer.semantic_weight}")
print(f"Lexical weight: {scorer.lexical_weight}\n")

# Find the two most recently created projects
recent_projects = projects.order_by('-created_at')[:2]
if recent_projects.count() == 2:
    p1, p2 = recent_projects[0], recent_projects[1]
    print(f"Comparing:")
    print(f"  Project 1: {p1.id} - {p1.title}")
    print(f"  Project 2: {p2.id} - {p2.title}\n")
    
    if p1.combined_embedding and p2.combined_embedding:
        print("✓ Both have embeddings\n")
        
        # Calculate similarity scores
        semantic_sim = scorer.calculate_semantic_similarity(p1.combined_embedding, p2.combined_embedding)
        lexical_sim = scorer.calculate_lexical_similarity(f"{p1.title} {p1.main_objective}", f"{p2.title} {p2.main_objective}")
        hybrid_sim = scorer.calculate_hybrid_similarity(p1.combined_embedding, p2.combined_embedding, p1.title, p2.title)
        
        print(f"Semantic similarity: {semantic_sim:.3f}")
        print(f"Lexical similarity: {lexical_sim:.3f}")
        print(f"Hybrid similarity: {hybrid_sim:.3f}\n")
        
        print(f"Would be auto-flagged? {hybrid_sim >= scorer.auto_flag_threshold}")
        print(f"DuplicateFlag exists? {DuplicateFlag.objects.filter(project=p1, similar_project=p2).exists()}\n")
    else:
        print(f"✗ Missing embeddings:")
        print(f"  Project 1 has combined_embedding: {p1.combined_embedding is not None}")
        print(f"  Project 2 has combined_embedding: {p2.combined_embedding is not None}\n")

# Show all duplicate flags
print("=" * 80)
print(f"Total DuplicateFlags: {DuplicateFlag.objects.count()}\n")
if DuplicateFlag.objects.exists():
    print("Sample flags (top 5 by score):")
    for flag in DuplicateFlag.objects.all().order_by('-similarity_score')[:5]:
        print(f"  {flag.project.title} <-> {flag.similar_project.title}: {flag.similarity_score:.3f}")
