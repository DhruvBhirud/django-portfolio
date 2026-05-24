from functools import wraps
import time
from django.core.cache import cache
from django.contrib import messages
from django.shortcuts import redirect

def ratelimit_post(limit=3, period=300):
    """
    Rate limit POST requests to a view function per IP address.
    
    :param limit: Maximum number of submissions allowed within the period.
    :param period: Time window in seconds.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if request.method == 'POST':
                # Determine client IP address
                x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
                if x_forwarded_for:
                    ip = x_forwarded_for.split(',')[0].strip()
                else:
                    ip = request.META.get('REMOTE_ADDR')
                
                cache_key = f"ratelimit_post_{view_func.__name__}_{ip}"
                request_history = cache.get(cache_key, [])
                
                now = time.time()
                # Clean up history: remove timestamps older than the rate limiting period
                request_history = [t for t in request_history if now - t < period]
                
                if len(request_history) >= limit:
                    # Calculate remaining wait time
                    oldest_request = request_history[0]
                    wait_time = int(period - (now - oldest_request))
                    wait_minutes = (wait_time + 59) // 60
                    
                    messages.error(
                        request, 
                        f"Too many submissions. Please wait {wait_minutes} minute(s) before trying again."
                    )
                    return redirect('index')
                
                # Log current submission timestamp
                request_history.append(now)
                cache.set(cache_key, request_history, period)
                
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
