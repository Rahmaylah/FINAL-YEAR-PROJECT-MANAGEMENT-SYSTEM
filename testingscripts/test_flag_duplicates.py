"""
Test script to manually flag the duplicate projects.

Run with: python test_flag_duplicates.py
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
from django.utils import timezone

def main():
    scorer = get_similarity_scorer()
    projects = list(Project.objects.all().order_by('id'))
    
    print("\n" + "=" * 80)
    print("MANUAL DUPLICATE FLAGGING TEST")
    print("=" * 80 + "\n")
    
    if len(projects) < 2:
        print("Need at least 2 projects to test")
        return
    
    p1, p2 = projects[0], projects[1]
    
    print(f"Project 1: {p1.id} - {p1.title}")
    print(f"Project 2: {p2.id} - {p2.title}\n")
    
    # Calculate similarity
    emb1 = p1.combined_embedding.tolist() if hasattr(p1.combined_embedding, 'tolist') else list(p1.combined_embedding)
    emb2 = p2.combined_embedding.tolist() if hasattr(p2.combined_embedding, 'tolist') else list(p2.combined_embedding)
    
    similarity_score = scorer.calculate_hybrid_similarity(emb1, emb2, p1.title, p2.title)
    
    print(f"Calculated similarity score: {similarity_score:.3f}")
    print(f"Auto-flag threshold: {scorer.auto_flag_threshold}")
    print(f"Should be auto-flagged: {similarity_score >= scorer.auto_flag_threshold}\n")
    
    # Try to create flag
    print("Creating DuplicateFlag records...\n")
    
    try:
        # Create flags both ways (A vs B and B vs A)
        flag1, created1 = DuplicateFlag.objects.get_or_create(
            project=p1,
            similar_project=p2,
            defaults={
                'similarity_score': similarity_score,
            }
        )
        
        flag2, created2 = DuplicateFlag.objects.get_or_create(
            project=p2,
            similar_project=p1,
            defaults={
                'similarity_score': similarity_score,
            }
        )
        
        print(f"Flag 1 created: {created1}")
        print(f"Flag 1: {flag1.id} - {flag1.project.title} <-> {flag1.similar_project.title}")
        print(f"Flag 1 score: {flag1.similarity_score:.3f}\n")
        
        print(f"Flag 2 created: {created2}")
        print(f"Flag 2: {flag2.id} - {flag2.project.title} <-> {flag2.similar_project.title}")
        print(f"Flag 2 score: {flag2.similarity_score:.3f}\n")
        
        # Update projects
        p1.is_flagged_duplicate = True
        p1.duplicate_check_score = similarity_score
        p1.last_similarity_check = timezone.now()
        p1.save()
        
        p2.is_flagged_duplicate = True
        p2.duplicate_check_score = similarity_score
        p2.last_similarity_check = timezone.now()
        p2.save()
        
        print("✓ Projects marked as duplicates")
        print(f"  P1: is_flagged_duplicate={p1.is_flagged_duplicate}, score={p1.duplicate_check_score}")
        print(f"  P2: is_flagged_duplicate={p2.is_flagged_duplicate}, score={p2.duplicate_check_score}\n")
        
        # Verify
        all_flags = DuplicateFlag.objects.all()
        print(f"Total DuplicateFlags in database now: {all_flags.count()}\n")
        
        for flag in all_flags:
            print(f"  {flag.id}: {flag.project.title} <-> {flag.similar_project.title}: {flag.similarity_score:.3f}")
        
    except Exception as e:
        print(f"✗ Error creating flags: {e}\n")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
