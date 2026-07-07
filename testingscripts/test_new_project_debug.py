"""
Test script to debug why the new project wasn't auto-flagged.

Run with: python test_new_project_debug.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fypms.settings')
sys.path.insert(0, '/home/revocajana/projects/fyp')
django.setup()

from projects.models import Project, DuplicateFlag
from projects.similarity import get_similarity_scorer

def main():
    print("\n" + "=" * 80)
    print("DEBUG: NEW PROJECT AUTO-FLAGGING")
    print("=" * 80 + "\n")
    
    # Get all projects
    projects = list(Project.objects.all().order_by('-created_at'))
    
    print(f"Total projects: {len(projects)}\n")
    
    if len(projects) < 1:
        print("No projects found!")
        return
    
    # Show project details
    print("PROJECT DETAILS:")
    for i, p in enumerate(projects[:3]):
        has_emb = "✓" if p.combined_embedding is not None else "✗"
        print(f"{i+1}. [{has_emb}] ID {p.id}: {p.title}")
        print(f"   Flagged: {p.is_flagged_duplicate}")
        print(f"   Score: {p.duplicate_check_score}")
        print(f"   Embeddings: title={p.title_embedding is not None}, obj={p.objectives_embedding is not None}, combined={p.combined_embedding is not None}\n")
    
    # Get newest project (should be the one just created)
    newest = projects[0]
    
    print(f"\nNewest project (ID {newest.id}): {newest.title}\n")
    
    # Check if it has embeddings
    if newest.combined_embedding is None:
        print("❌ NEW PROJECT HAS NO EMBEDDINGS!")
        print("   The signal may not have run yet.\n")
        return
    
    print("✓ New project has embeddings\n")
    
    # Convert embeddings to lists
    title_emb = newest.title_embedding.tolist() if hasattr(newest.title_embedding, 'tolist') else (list(newest.title_embedding) if newest.title_embedding else None)
    obj_emb = newest.objectives_embedding.tolist() if hasattr(newest.objectives_embedding, 'tolist') else (list(newest.objectives_embedding) if newest.objectives_embedding else None)
    combined_emb = newest.combined_embedding.tolist() if hasattr(newest.combined_embedding, 'tolist') else (list(newest.combined_embedding) if newest.combined_embedding else None)
    
    # Compare with all other projects
    scorer = get_similarity_scorer()
    
    print("COMPARING WITH OTHER PROJECTS:")
    for p in projects[1:]:
        if p.combined_embedding is None:
            print(f"  SKIP {p.id}: No embeddings")
            continue
        
        p_emb = p.combined_embedding.tolist() if hasattr(p.combined_embedding, 'tolist') else (list(p.combined_embedding) if p.combined_embedding else None)
        
        score = scorer.calculate_hybrid_similarity(combined_emb, p_emb, newest.title, p.title)
        is_auto_flag = score >= scorer.auto_flag_threshold
        
        print(f"  vs {p.id}: {score:.3f} {'🔴 AUTO-FLAG' if is_auto_flag else '✓'}")
    
    # Check existing flags for newest project
    print(f"\nEXISTING FLAGS FOR PROJECT {newest.id}:")
    flags = DuplicateFlag.objects.filter(project=newest)
    if flags.exists():
        for flag in flags:
            print(f"  → {flag.similar_project.id}: {flag.similarity_score:.3f}")
    else:
        print("  None")
    
    print("\nSUMMARY:")
    print(f"  Embeddings generated: {newest.combined_embedding is not None}")
    print(f"  Flagged as duplicate: {newest.is_flagged_duplicate}")
    print(f"  Duplicate check score: {newest.duplicate_check_score}")

if __name__ == '__main__':
    main()
