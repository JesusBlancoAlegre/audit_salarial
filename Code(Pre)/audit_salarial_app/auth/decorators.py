from functools import wraps
from flask import abort
from flask_login import login_required, current_user

def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role_name not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapper
    return decorator