"""Proteção de rotas com sessão, token e role."""

from functools import wraps
from flask import session, redirect, request
from src.app.utils.security import SecurityManager
from src.config.app import aplicacao

security = SecurityManager(aplicacao.config['SECRET_KEY'])


def login_required(role=None):
    """Bloqueia acesso sem sessão/token válidos ou role compatível."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if "usuario_logado" not in session:
                return redirect("/")

            token = request.cookies.get('auth_token')
            if not token:
                session.clear()
                return redirect("/")

            token_data = security.verify_token(token)
            if not token_data:
                session.clear()
                return redirect("/")

            if token_data.get('email') != session.get("usuario_logado"):
                session.clear()
                return redirect("/")

            if role:
                user_role = session.get("tipo")
                allowed_roles = [role] if isinstance(role, str) else role
                if user_role not in allowed_roles:
                    if user_role == 'Admin':
                        return redirect("/admin/dashboard")
                    elif user_role == 'Escuderia':
                        return redirect("/escuderia/dashboard")
                    elif user_role == 'Piloto':
                        return redirect("/piloto/dashboard")
                    else:
                        session.clear()
                        return redirect("/")

            return func(*args, **kwargs)
        return wrapper

    if callable(role):
        f = role
        role = None
        return decorator(f)

    return decorator
