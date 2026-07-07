"""
Manual duplicate check script to force-flag all projects.

Run with: python test_force_flag_all.py
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
    print("\n" + "=" * 80)
    print("FORCE FLAG ALL PROJECTS")
    print("=" * 80 + "\n")
    
    scorer = get_similarity_scorer()
    projects = list(Project.objects.all().order_by('id'))
    
    print(f"Processing {len(projects)} projects...\n")
    
    for project in projects:
        if project.combined_embedding is None:
            print(f"SKIP {project.id}: No embeddings")
            continue
        
        # Convert embeddings to lists
        title_emb = project.title_embedding.tolist() if hasattr(project.title_embedding, 'tolist') else (list(project.title_embedding) if project.title_embedding else None)
        obj_emb = project.objectives_embedding.tolist() if hasattr(project.objectives_embedding, 'tolist') else (list(project.objectives_embedding) if project.objectives_embedding else None)
        combined_emb = project.combined_embedding.tolist() if hasattr(project.combined_embedding, 'tolist') else (list(project.combined_embedding) if project.combined_embedding else None)
        
        # Find similar projects
        similar_projects = scorer.find_similar_projects(
            project_id=project.id,
            title=project.title,
            objectives=f"{project.main_objective}",
            title_embedding=title_emb,
            objectives_embedding=obj_emb,
            combined_embedding=combined_emb,
            limit=10
        )
        
        if not similar_projects:
            print(f"✓ {project.id}: No similar projects")
            continue
        
        # Find max similarity
        max_similarity = max(s['hybrid_similarity'] for s in similar_projects)
        
        # Create flags for all auto-flag matches
        flags_created = 0
        for similar in similar_projects:
            if similar['auto_flag']:
                flag, created = DuplicateFlag.objects.get_or_create(
                    project=project,
                    similar_project_id=similar['id'],
                    defaults={
                        'similarity_score': similar['hybrid_similarity'],
                    }
                )
                if created:
                    flags_created += 1
        
        # Update project
        project.duplicate_check_score = max_similarity
        project.is_flagged_duplicate = (flags_created > 0)
        project.last_similarity_check = timezone.now()
        project.save(update_fields=['duplicate_check_score', 'is_flagged_duplicate', 'last_similarity_check'])
        
        status = f"🚩 FLAGGED ({flags_created} new flags)" if flags_created > 0 else f"✓ {len(similar_projects)} similar"
        print(f"{project.id}: {status} | Score: {max_similarity:.3f}")
    
    # Show final summary
    print("\n" + "=" * 80)
    print("FINAL STATUS")
    print("=" * 80 + "\n")
    
    flagged_count = Project.objects.filter(is_flagged_duplicate=True).count()
    total_count = Project.objects.count()
    total_flags = DuplicateFlag.objects.count()
    
    print(f"Projects flagged as duplicates: {flagged_count}/{total_count}")
    print(f"Total DuplicateFlag records: {total_flags}\n")
    
    for p in Project.objects.all().order_by('id'):
        flag_indicator = "🚩" if p.is_flagged_duplicate else " "
        score = f"{p.duplicate_check_score:.3f}" if p.duplicate_check_score else "None"
        print(f"  {p.id}: {flag_indicator} {p.title[:40]:40} | Score: {score:6}")

if __name__ == '__main__':
    main()
