from functools import wraps
from flask import session, redirect, request
from src.app.utils.security import SecurityManager
from src.config.app import aplicacao

# Instância global do gerenciador de segurança
security = SecurityManager(aplicacao.config['SECRET_KEY'])

def login_required(role=None):
    """
    Decorator para proteger rotas que requerem autenticação e autorização por tipo/role.
    Aceita strings simples ou listas de roles permitidos.
    Pode ser usado como @login_required ou @login_required(role='Admin').
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Verifica se há usuário na sessão
            if "usuario_logado" not in session:
                return redirect("/")
            
            # Verifica token no cookie
            token = request.cookies.get('auth_token')
            if not token:
                session.clear()
                return redirect("/")
            
            # Valida o token
            token_data = security.verify_token(token)
            if not token_data:
                session.clear()
                return redirect("/")
            
            # Verifica se o login do token corresponde ao da sessão
            if token_data.get('email') != session.get("usuario_logado"):
                session.clear()
                return redirect("/")
            
            # Validação baseada em tipo/role se especificado
            if role:
                user_role = session.get("tipo")
                allowed_roles = [role] if isinstance(role, str) else role
                if user_role not in allowed_roles:
                    # Se não tiver permissão, redireciona para seu próprio dashboard correspondente
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

    # Trata caso de uso direto sem parâmetros: @login_required
    if callable(role):
        f = role
        role = None
        return decorator(f)
        
    return decorator
