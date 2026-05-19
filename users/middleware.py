from django.shortcuts import redirect
from django.utils import timezone
from django.urls import resolve
from django.contrib import messages

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
        allowed_urls = ['pricing', 'login', 'signup', 'logout', 'contact_sales']
        if current_url_name in allowed_urls:
            return self.get_response(request)

        # 3. Check for trial expiration
        if workspace.subscription_status == 'TRIAL':
            if workspace.trial_ends_at and timezone.now() > workspace.trial_ends_at:
                if not request.path.startswith('/static/') and not request.path.startswith('/media/'):
                    messages.warning(
                        request,
                        'TRIAL_EXPIRED'
                    )
                    return redirect('frontend:pricing')

        # 4. Check for Past Due / Canceled status
        if workspace.subscription_status in ['PAST_DUE', 'CANCELED']:
            if current_url_name not in allowed_urls:
                reason = 'PAYMENT_PAST_DUE' if workspace.subscription_status == 'PAST_DUE' else 'SUBSCRIPTION_CANCELED'
                messages.warning(request, reason)
                return redirect('frontend:pricing')

        response = self.get_response(request)
        return response
