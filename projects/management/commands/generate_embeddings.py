"""
Management command to generate embeddings for projects.

Usage:
    python manage.py generate_embeddings              # Generate for projects without embeddings
    python manage.py generate_embeddings --all        # Regenerate for all projects
    python manage.py generate_embeddings --project-id 123  # Generate for specific project
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from projects.models import Project
from projects.utils import generate_project_embeddings
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate embeddings for projects'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Regenerate embeddings for all projects',
        )
        parser.add_argument(
            '--project-id',
            type=int,
            help='Generate embeddings for a specific project ID',
        )

    def handle(self, *args, **options):
        if options['project_id']:
            # Generate for specific project
            try:
                project = Project.objects.get(id=options['project_id'])
                self.generate_for_project(project)
                self.stdout.write(
                    self.style.SUCCESS(f'✓ Generated embeddings for project {project.id}')
                )
            except Project.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'✗ Project with ID {options["project_id"]} not found')
                )
        elif options['all']:
            # Regenerate for all projects
            projects = Project.objects.all()
            self.stdout.write(
                self.style.WARNING(f'Regenerating embeddings for {projects.count()} projects...')
            )
            self.generate_for_queryset(projects)
        else:
            # Generate for projects without embeddings
            projects = Project.objects.filter(combined_embedding__isnull=True)
            self.stdout.write(
                self.style.WARNING(f'Generating embeddings for {projects.count()} projects without embeddings...')
            )
            self.generate_for_queryset(projects)

    def generate_for_queryset(self, queryset):
        """Generate embeddings for a queryset of projects."""
        total = queryset.count()
        success = 0
        failed = 0

        for i, project in enumerate(queryset, 1):
            try:
                self.generate_for_project(project)
                success += 1
                self.stdout.write(f'  [{i}/{total}] ✓ {project.title}')
            except Exception as e:
                failed += 1
                logger.error(f'Failed to generate embeddings for project {project.id}: {e}')
                self.stdout.write(f'  [{i}/{total}] ✗ {project.title} - {str(e)}')

        self.stdout.write(self.style.SUCCESS(f'\n✓ Completed: {success} succeeded, {failed} failed'))

    def generate_for_project(self, project):
        """Generate and save embeddings for a single project."""
        embeddings = generate_project_embeddings(
            title=project.title,
            objectives=project.main_objective,
            description=project.project_description
        )

        if embeddings and embeddings.get('combined_embedding'):
            project.title_embedding = embeddings.get('title_embedding')
            project.objectives_embedding = embeddings.get('objectives_embedding')
            project.combined_embedding = embeddings.get('combined_embedding')
            project.last_similarity_check = timezone.now()
            project.save(update_fields=[
                'title_embedding',
                'objectives_embedding',
                'combined_embedding',
                'last_similarity_check'
            ])
        else:
            raise Exception('Failed to generate valid embeddings')
