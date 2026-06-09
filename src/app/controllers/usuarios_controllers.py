"""
Controller de Autenticação — gerencia login, logout e criação de sessão.

Conceito de BD: Autenticação contra tabela USERS com controle de sessão.
------------------------------------------------------------------------
O processo de login envolve:
  1. Validação das credenciais contra a tabela USERS do banco (via DAO)
  2. Geração de token de sessão assinado (HMAC)
  3. Armazenamento do perfil do usuário na sessão Flask
  4. Registro da ação de LOGIN na tabela USERS_LOG (auditoria)
  5. Redirecionamento baseado no campo 'tipo' do usuário (RBAC)

Conceito de Auditoria (USERS_LOG):
  - Toda entrada (LOGIN) e saída (LOGOUT) é registrada com timestamp
  - Permite rastrear quem acessou o sistema e quando
  - A tabela USERS_LOG tem FK para USERS (integridade referencial)
"""

from src.app.BD.usuarios_dao import Usuarios_dao
from src.app.utils.security import SecurityManager
from src.config.database import connection_pool
from src.config.app import aplicacao
from flask import redirect, request, session, make_response


class UsuariosControllers:
    """
    Controller responsável pelo processo de autenticação.
    
    Implementa o fluxo completo de login:
      BD (validação) → sessão (estado) → cookie (token) → auditoria (log)
    """

    def __init__(self):
        """Inicializa o controller com o gerenciador de segurança (bcrypt + tokens)."""
        self.security = SecurityManager(aplicacao.config['SECRET_KEY'])

    def valida_acesso_usuario(self):
        """
        Processa o formulário de login (POST /validaBDUsuarios).

        Fluxo completo de autenticação:
        --------------------------------
        1. Coleta login/senha do formulário POST
        2. Chama Usuarios_dao.select_na_tabela_usuarios():
           → SELECT na tabela USERS filtrado pelo login (coluna UNIQUE)
           → Verifica senha com bcrypt.checkpw() (sem armazenar texto plano)
           → Levanta Exception em caso de credenciais inválidas
        3. Gera token HMAC assinado com a SECRET_KEY da aplicação
        4. Armazena dados na sessão Flask (server-side):
           - usuario_logado: login do usuário (usado para validação futura)
           - userid: PK do usuário em USERS (usado na auditoria)
           - tipo: perfil ('Admin', 'Escuderia', 'Piloto') — controla RBAC
           - id_original: FK para drivers.id ou constructors.id
        5. Registra ação de LOGIN na tabela USERS_LOG (auditoria)
        6. Redireciona para o dashboard correspondente ao perfil
        7. Define cookie 'auth_token' com proteções de segurança:
           - httponly=True: inacessível via JavaScript (proteção XSS)
           - samesite='Lax': proteção básica contra CSRF
           - max_age=86400: expira em 24 horas (86400 segundos)

        Conceito de campo 'tipo' como discriminador de perfil:
          O campo 'tipo' em USERS {'Admin', 'Escuderia', 'Piloto'} implementa
          a tipagem de usuário no banco — um único SELECT retorna o perfil
          e a aplicação decide o redirecionamento sem precisar de queries
          adicionais por tabela.
        """
        def view():
            usuario_dao = Usuarios_dao(connection_pool)
            try:
                # Coleta credenciais do corpo da requisição POST
                login = request.form.get("login")
                senha = request.form.get("senha")

                # Valida credenciais contra a tabela USERS:
                # → busca por login (UNIQUE index), verifica hash bcrypt
                usuario = usuario_dao.select_na_tabela_usuarios(login, senha)

                if usuario:
                    print(f"USUÁRIO {login} VALIDADO COM SUCESSO!")

                    # Gera token HMAC assinado (URLSafeTimedSerializer do itsdangerous)
                    # O token codifica o login e é assinado com a SECRET_KEY
                    token = self.security.generate_token(usuario['login'])

                    # Armazena dados do usuário na sessão server-side do Flask
                    # A sessão é um dicionário seguro — armazenado no servidor,
                    # referenciado por um cookie de sessão criptografado no cliente
                    session["usuario_logado"] = usuario['login']    # Para validação futura no decorator
                    session["userid"] = usuario['userid']            # Para auditoria no logout
                    session["tipo"] = usuario['tipo']                # Para RBAC nos decorators
                    session["id_original"] = usuario['id_original']  # FK para drivers ou constructors

                    # Registra ação de LOGIN na tabela USERS_LOG (auditoria do BD)
                    usuario_dao.registrar_log_auditoria(usuario['userid'], 'LOGIN')

                    # Redireciona para o dashboard do perfil correspondente
                    # (campo 'tipo' do banco determina a URL de destino)
                    if usuario['tipo'] == 'Admin':
                        response = make_response(redirect("/admin/dashboard"))
                    elif usuario['tipo'] == 'Escuderia':
                        response = make_response(redirect("/escuderia/dashboard"))
                    elif usuario['tipo'] == 'Piloto':
                        response = make_response(redirect("/piloto/dashboard"))
                    else:
                        response = make_response(redirect("/"))

                    # Define cookie com token de autenticação e proteções de segurança
                    response.set_cookie(
                        'auth_token',
                        token,
                        max_age=86400,   # Expira em 24 horas (em segundos)
                        httponly=True,   # Proteção XSS: JavaScript não pode ler o cookie
                        secure=False,    # Em produção com HTTPS: usar secure=True
                        samesite='Lax'   # Proteção CSRF: bloqueia envio cross-site
                    )

                    return response

            except Exception as erro:
                print(f"ERRO NA AUTENTICAÇÃO: {erro}")
                # Redireciona para login com flag de erro (sem expor detalhes do erro)
                return redirect("/?error=1")

        return view
