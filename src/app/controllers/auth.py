"""
Módulo de controle de autenticação e autorização baseada em roles.

Conceitos de BD / Sistema aplicados neste módulo:
  - Sessão de usuário (server-side session via Flask)
  - Autenticação stateful: o estado de "estar logado" é mantido na sessão
  - Autorização por Role (RBAC - Role-Based Access Control):
    o campo 'tipo' do banco (Admin / Escuderia / Piloto) define o que
    cada usuário pode acessar no sistema.
  - Token de autenticação (cookie httpOnly) como segunda camada de segurança
"""

from functools import wraps
from flask import session, redirect, request
from src.app.utils.security import SecurityManager
from src.config.app import aplicacao

# Instância global do gerenciador de segurança — compartilhada por todas as verificações
security = SecurityManager(aplicacao.config['SECRET_KEY'])


def login_required(role=None):
    """
    Decorator de proteção de rotas: verifica autenticação e autorização por role.

    Conceito de Sistema de BD: Controle de Acesso Baseado em Roles (RBAC).
    ----------------------------------------------------------------------
    O campo 'tipo' na tabela USERS do banco ('Admin', 'Escuderia', 'Piloto')
    define o papel/permissão de cada usuário. Este decorator implementa o
    controle de acesso verificando esse campo (armazenado na sessão Flask).

    Fluxo de verificação (dupla camada de segurança):
      1. Verifica se há usuário na sessão server-side (Flask session)
         → A sessão é armazenada no servidor e referenciada por um cookie
           de sessão assinado (não manipulável pelo cliente)
      2. Verifica o cookie 'auth_token' (token assinado com HMAC)
         → Proteção adicional: mesmo que a sessão seja válida, o token
           deve existir e ser válido
      3. Valida que o login do token corresponde ao login da sessão
         → Evita que um token de outra sessão seja reutilizado
      4. Verifica se o 'tipo' do usuário está nos roles permitidos
         → Implementação do RBAC: cada rota define quais roles podem acessá-la

    Uso flexível:
      @login_required           → qualquer usuário autenticado
      @login_required(role='Admin')       → apenas Admin
      @login_required(role=['Admin', 'Escuderia']) → Admin ou Escuderia

    O uso de @wraps(func) preserva o nome e docstring da função original,
    evitando problemas de roteamento no Flask.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # CAMADA 1: verifica sessão server-side
            if "usuario_logado" not in session:
                return redirect("/")

            # CAMADA 2: verifica cookie de token JWT-like (assinado com HMAC)
            token = request.cookies.get('auth_token')
            if not token:
                # Limpa sessão inconsistente (sessão sem token = estado inválido)
                session.clear()
                return redirect("/")

            # Valida assinatura e expiração (24h) do token
            token_data = security.verify_token(token)
            if not token_data:
                session.clear()
                return redirect("/")

            # CAMADA 3: garante que o token pertence ao usuário da sessão atual
            # (evita que tokens de outras sessões sejam reutilizados)
            if token_data.get('email') != session.get("usuario_logado"):
                session.clear()
                return redirect("/")

            # CAMADA 4: RBAC — verifica se o tipo/role do usuário tem permissão
            if role:
                user_role = session.get("tipo")  # 'Admin', 'Escuderia' ou 'Piloto'
                allowed_roles = [role] if isinstance(role, str) else role
                if user_role not in allowed_roles:
                    # Redireciona para o dashboard correto do tipo do usuário
                    # (em vez de exibir erro 403, melhora a experiência do usuário)
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

    # Trata o caso especial de @login_required sem parênteses
    # Nesse caso, 'role' recebe a função diretamente (não uma string)
    if callable(role):
        f = role
        role = None
        return decorator(f)

    return decorator
