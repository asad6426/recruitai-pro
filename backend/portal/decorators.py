from functools import wraps

from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect


def role_required(role):
    """Gates a view to a logged-in user with the given accounts.User.Role value.
    Sends role-less users to role_select, and wrong-role users to their own
    dashboard rather than 403ing them."""

    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            if not request.user.role:
                return redirect("role_select")
            if request.user.role != role:
                return redirect("login_redirect")
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
