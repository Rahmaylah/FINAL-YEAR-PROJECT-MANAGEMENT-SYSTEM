"""
Management command to run bulk duplicate detection.

Usage:
    python manage.py bulk_duplicate_check
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from projects.models import Project
from projects.similarity import get_similarity_scorer
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Run bulk duplicate detection on all projects'

    def handle(self, *args, **options):
        scorer = get_similarity_scorer()
        projects = Project.objects.all()
        
        self.stdout.write(f'Running duplicate detection on {projects.count()} projects...')
        
        results = []
        total_auto_flagged = 0
        
        for project in projects:
            try:
                # Convert embeddings from numpy arrays to lists if needed
                title_emb = project.title_embedding.tolist() if hasattr(project.title_embedding, 'tolist') else (list(project.title_embedding) if project.title_embedding else None)
                obj_emb = project.objectives_embedding.tolist() if hasattr(project.objectives_embedding, 'tolist') else (list(project.objectives_embedding) if project.objectives_embedding else None)
                combined_emb = project.combined_embedding.tolist() if hasattr(project.combined_embedding, 'tolist') else (list(project.combined_embedding) if project.combined_embedding else None)
                
                # Find similar projects
                similar_projects = scorer.find_similar_projects(
                    project_id=project.id,
                    title=project.title,
                    objectives=f"{project.main_objective} {project.specific_objectives}",
                    title_embedding=title_emb,
                    objectives_embedding=obj_emb,
                    combined_embedding=combined_emb,
                    limit=5
                )
                
                # Auto-flag projects above threshold
                auto_flagged_new = 0
                auto_flagged_existing = 0
                for similar in similar_projects:
                    if similar['auto_flag']:
                        # Create duplicate flag if it doesn't exist
                        from projects.models import DuplicateFlag
                        flag, created = DuplicateFlag.objects.get_or_create(
                            project=project,
                            similar_project_id=similar['id'],
                            defaults={
                                'similarity_score': similar['hybrid_similarity'],
                            }
                        )
                        if created:
                            auto_flagged_new += 1
                            total_auto_flagged += 1
                        else:
                            auto_flagged_existing += 1
                        # Mark project as flagged if any matching duplicate exists
                        project.is_flagged_duplicate = True
                        project.save(update_fields=['is_flagged_duplicate'])
                
                # Update duplicate check score with highest similarity
                if similar_projects:
                    max_similarity = max(s['hybrid_similarity'] for s in similar_projects)
                    project.duplicate_check_score = max_similarity
                    project.save(update_fields=['duplicate_check_score'])
                
                # Update last similarity check timestamp
                project.last_similarity_check = timezone.now()
                project.save(update_fields=['last_similarity_check'])
                
                results.append({
                    'project_id': project.id,
                    'project_title': project.title,
                    'similar_projects_found': len(similar_projects),
                    'auto_flagged_new': auto_flagged_new,
                    'auto_flagged_existing': auto_flagged_existing,
                    'max_similarity_score': max_similarity if similar_projects else None,
                    'processed': True
                })
                
                self.stdout.write(f'  ✓ {project.title} - {len(similar_projects)} similar, {auto_flagged_new} new flags, {auto_flagged_existing} existing')
                
            except Exception as e:
                logger.error(f"Failed to process project {project.id}: {e}")
                results.append({
                    'project_id': project.id,
                    'project_title': project.title,
                    'error': str(e),
                    'processed': False
                })
                self.stdout.write(f'  ✗ {project.title} - {str(e)}')
        
        self.stdout.write(self.style.SUCCESS(f'\nCompleted: {len([r for r in results if r["processed"]])} processed, {total_auto_flagged} new flags created'))