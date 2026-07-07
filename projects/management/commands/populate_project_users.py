from django.core.management.base import BaseCommand
from projects.models import Project, ProjectUser

class Command(BaseCommand):
    help = 'Populate missing ProjectUser entries for existing projects'

    def handle(self, *args, **options):
        projects_without_users = []
        created_count = 0

        for project in Project.objects.all():
            # Check if ProjectUser entry exists for the project creator
            if not ProjectUser.objects.filter(project=project, user=project.user).exists():
                ProjectUser.objects.create(
                    project=project,
                    user=project.user,
                    role='lead'
                )
                created_count += 1
                self.stdout.write(f'Created ProjectUser for project: {project.title} -> {project.user.username}')
            else:
                projects_without_users.append(project)

        self.stdout.write(self.style.SUCCESS(f'Created {created_count} ProjectUser entries'))

        if projects_without_users:
            self.stdout.write(f'Projects that already have ProjectUser entries: {len(projects_without_users)}')