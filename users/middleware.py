from django.shortcuts import redirect
from django.utils import timezone
from django.urls import resolve

class SubscriptionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Skip checks for unauthenticated users or non-workspace users
        if not request.user.is_authenticated or not hasattr(request.user, 'workspace') or not request.user.workspace:
            return self.get_response(request)

        workspace = request.user.workspace
        current_url_name = resolve(request.path_info).url_name

        # 2. Skip checks for essential pages to allow upgrading/viewing pricing
        # We assume these are in the 'frontend' namespace based on previous view checks
        allowed_urls = ['pricing', 'login', 'signup', 'logout', 'contact_sales']
        if current_url_name in allowed_urls:
            return self.get_response(request)

        # 3. Check for trial expiration
        if workspace.subscription_status == 'TRIAL':
            if workspace.trial_ends_at and timezone.now() > workspace.trial_ends_at:
                # Trial expired
                # For now, we just attach a flag to the request so views/templates can show a banner
                # or we could redirect to pricing. 
                # Let's redirect to pricing if they try to access 'active' dashboard areas
                # But only if it's not a static or media file
                if not request.path.startswith('/static/') and not request.path.startswith('/media/'):
                    return redirect('frontend:pricing')

        # 4. Check for Past Due / Canceled status
        if workspace.subscription_status in ['PAST_DUE', 'CANCELED']:
            if current_url_name not in allowed_urls:
                return redirect('frontend:pricing')

        response = self.get_response(request)
        return response
