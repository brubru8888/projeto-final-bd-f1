from src.app.BD.usuarios_dao import Usuarios_dao
from src.app.utils.security import SecurityManager
from src.config.database import connection_pool
from src.config.app import aplicacao
from flask import redirect, request, session, make_response

class UsuariosControllers:
    def __init__(self):
        """Inicializa o controller com gerenciador de segurança"""
        self.security = SecurityManager(aplicacao.config['SECRET_KEY'])
    
    def valida_acesso_usuario(self):
        def view():
            usuario_dao = Usuarios_dao(connection_pool)
            try:
                login = request.form.get("login")
                senha = request.form.get("senha")
                
                # Valida credenciais usando a nova tabela USERS
                usuario = usuario_dao.select_na_tabela_usuarios(login, senha)

                if usuario:
                    print(f"USUÁRIO {login} VALIDADO COM SUCESSO!")
                    
                    # Gera token seguro baseado no login (que substitui o email do green_check)
                    token = self.security.generate_token(usuario['login'])
                    
                    # Armazena dados na sessão
                    session["usuario_logado"] = usuario['login']
                    session["userid"] = usuario['userid']
                    session["tipo"] = usuario['tipo']
                    session["id_original"] = usuario['id_original']
                    
                    # Registrar log de auditoria de login
                    usuario_dao.registrar_log_auditoria(usuario['userid'], 'LOGIN')
                    
                    # Redireciona de acordo com o papel do usuário
                    if usuario['tipo'] == 'Admin':
                        response = make_response(redirect("/admin/dashboard"))
                    elif usuario['tipo'] == 'Escuderia':
                        response = make_response(redirect("/escuderia/dashboard"))
                    elif usuario['tipo'] == 'Piloto':
                        response = make_response(redirect("/piloto/dashboard"))
                    else:
                        response = make_response(redirect("/"))
                        
                    # Cria resposta e define cookie com token
                    response.set_cookie(
                        'auth_token',
                        token,
                        max_age=86400,  # 24 horas em segundos
                        httponly=True,  # Proteção contra XSS
                        secure=False,   # True em produção com HTTPS
                        samesite='Lax'  # Proteção contra CSRF
                    )
                    
                    return response

            except Exception as erro:
                print(f"ERRO NA AUTENTICAÇÃO: {erro}")
                # Exibe mensagem de erro na página de login (pode ser passada via query string ou flash)
                return redirect("/?error=1")

        return view
