import socket
import subprocess
import re
from pathlib import Path
from django.core.management.base import BaseCommand
from django.conf import settings


class Command(BaseCommand):
    help = 'Auto-detect current network IP and update .env file for adaptive networking'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )

    def get_network_ip(self):
        """Get the current network IP address"""
        try:
            # Try to get IP using socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))  # Connect to Google DNS
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            # Fallback: try to parse ifconfig output
            try:
                result = subprocess.run(['ifconfig'], capture_output=True, text=True)
                # Look for inet addr in ifconfig output (Linux)
                match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)', result.stdout)
                if match:
                    ip = match.group(1)
                    if not ip.startswith('127.'):
                        return ip
            except Exception:
                pass

            # Last resort: try hostname -I
            try:
                result = subprocess.run(['hostname', '-I'], capture_output=True, text=True)
                ips = result.stdout.strip().split()
                for ip in ips:
                    if not ip.startswith('127.'):
                        return ip
            except Exception:
                pass

        return None

    def update_env_file(self, current_ip, dry_run=False):
        """Update the .env file with new network configuration"""
        env_path = Path(settings.BASE_DIR) / '.env'

        if not env_path.exists():
            self.stdout.write(self.style.WARNING(f'.env file not found at {env_path}'))
            return

        # Read current .env content
        with open(env_path, 'r') as f:
            content = f.read()

        # Update ALLOWED_HOSTS
        allowed_hosts_match = re.search(r'ALLOWED_HOSTS=(.+)', content)
        if allowed_hosts_match:
            current_hosts = allowed_hosts_match.group(1)
            if current_ip not in current_hosts:
                new_hosts = f"{current_hosts},{current_ip}"
                content = content.replace(f'ALLOWED_HOSTS={current_hosts}', f'ALLOWED_HOSTS={new_hosts}')
                self.stdout.write(f"Updated ALLOWED_HOSTS: {current_hosts} -> {new_hosts}")

        # Update CORS_ORIGINS
        cors_match = re.search(r'CORS_ORIGINS=(.+)', content)
        if cors_match:
            current_origins = cors_match.group(1)
            frontend_ports = [3000, 3001]  # Common React dev ports
            new_origins = current_origins

            for port in frontend_ports:
                origin = f"http://{current_ip}:{port}"
                if origin not in current_origins:
                    new_origins = f"{new_origins},{origin}"
                    self.stdout.write(f"Added CORS origin: {origin}")

            if new_origins != current_origins:
                content = content.replace(f'CORS_ORIGINS={current_origins}', f'CORS_ORIGINS={new_origins}')

        # Update CSRF_ORIGINS
        csrf_match = re.search(r'CSRF_ORIGINS=(.+)', content)
        if csrf_match:
            current_origins = csrf_match.group(1)
            frontend_ports = [3000, 3001]
            new_origins = current_origins

            for port in frontend_ports:
                origin = f"http://{current_ip}:{port}"
                if origin not in current_origins:
                    new_origins = f"{new_origins},{origin}"
                    self.stdout.write(f"Added CSRF origin: {origin}")

            if new_origins != current_origins:
                content = content.replace(f'CSRF_ORIGINS={current_origins}', f'CSRF_ORIGINS={new_origins}')

        if dry_run:
            self.stdout.write(self.style.SUCCESS('DRY RUN - No changes made'))
            self.stdout.write('New .env content would be:')
            self.stdout.write(content)
        else:
            # Write updated content
            with open(env_path, 'w') as f:
                f.write(content)
            self.stdout.write(self.style.SUCCESS(f'Updated .env file with IP: {current_ip}'))

    def handle(self, *args, **options):
        dry_run = options['dry_run']

        self.stdout.write('Detecting current network IP...')

        current_ip = self.get_network_ip()

        if not current_ip:
            self.stdout.write(self.style.ERROR('Could not detect network IP address'))
            self.stdout.write('Make sure you are connected to a network')
            return

        self.stdout.write(f'Current network IP: {current_ip}')

        # Check if IP is already configured
        if current_ip in settings.ALLOWED_HOSTS:
            self.stdout.write(self.style.SUCCESS(f'IP {current_ip} is already configured'))
        else:
            self.stdout.write(f'IP {current_ip} needs to be added to configuration')
            self.update_env_file(current_ip, dry_run)

        if not dry_run:
            self.stdout.write(self.style.SUCCESS('\nConfiguration updated!'))
            self.stdout.write('Restart your Django server for changes to take effect:')
            self.stdout.write('  python manage.py runserver 0.0.0.0:8000')
            self.stdout.write('\nThen restart your React dev server:')
            self.stdout.write('  cd frontend && npm start')