"""Login, logout e criação de sessão."""

from src.app.BD.usuarios_dao import Usuarios_dao
from src.app.utils.security import SecurityManager
from src.config.database import connection_pool
from src.config.app import aplicacao
from flask import redirect, request, session, make_response


class UsuariosControllers:
    """Processa autenticação e auditoria."""

    def __init__(self):
        self.security = SecurityManager(aplicacao.config['SECRET_KEY'])

    def valida_acesso_usuario(self):
        """Valida credenciais, cria sessão e registra login."""
        def view():
            usuario_dao = Usuarios_dao(connection_pool)
            try:
                login = request.form.get("login")
                senha = request.form.get("senha")

                usuario = usuario_dao.select_na_tabela_usuarios(login, senha)

                if usuario:
                    print(f"USUÁRIO {login} VALIDADO COM SUCESSO!")

                    token = self.security.generate_token(usuario['login'])

                    session["usuario_logado"] = usuario['login']
                    session["userid"] = usuario['userid']
                    session["tipo"] = usuario['tipo']
                    session["id_original"] = usuario['id_original']

                    usuario_dao.registrar_log_auditoria(usuario['userid'], 'LOGIN')

                    if usuario['tipo'] == 'Admin':
                        response = make_response(redirect("/admin/dashboard"))
                    elif usuario['tipo'] == 'Escuderia':
                        response = make_response(redirect("/escuderia/dashboard"))
                    elif usuario['tipo'] == 'Piloto':
                        response = make_response(redirect("/piloto/dashboard"))
                    else:
                        response = make_response(redirect("/"))

                    response.set_cookie(
                        'auth_token',
                        token,
                        max_age=86400,
                        httponly=True,
                        secure=False,
                        samesite='Lax'
                    )

                    return response

            except Exception as erro:
                print(f"ERRO NA AUTENTICAÇÃO: {erro}")
                return redirect("/?error=1")

        return view
