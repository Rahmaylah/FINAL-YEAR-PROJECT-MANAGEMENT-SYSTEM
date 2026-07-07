from django.utils.deprecation import MiddlewareMixin
import re

class CSRFExemptMiddleware(MiddlewareMixin):
    """Exempt API endpoints from CSRF protection"""
    
    exempt_urls = [
        r'^/api/',
    ]
    
    def process_request(self, request):
        # Check if request path matches exempt URLs
        for pattern in self.exempt_urls:
            if re.match(pattern, request.path):
                request._dont_enforce_csrf_checks = True
        return None
