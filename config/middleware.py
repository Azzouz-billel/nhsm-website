"""Project-level middleware."""


class PermissionsPolicyMiddleware:
    """Send a restrictive Permissions-Policy header on every response, switching
    off browser features the site never uses (defence-in-depth)."""

    POLICY = "geolocation=(), camera=(), microphone=(), payment=(), usb=()"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response["Permissions-Policy"] = self.POLICY
        return response
