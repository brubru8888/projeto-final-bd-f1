from src.app.controllers.usuarios_controllers import UsuariosControllers
from src.app.controllers.admin_controllers import AdminControllers
from src.app.controllers.escuderia_controllers import EscuderiaControllers
from src.app.controllers.piloto_controllers import PilotoControllers
from src.app.controllers.auth import login_required
from flask import render_template, session, redirect, request

usuario_cont = UsuariosControllers()
admin_cont = AdminControllers()
escuderia_cont = EscuderiaControllers()
piloto_cont = PilotoControllers()

def rotas(aplicacao):
    # Evitar problema com o CORS
    @aplicacao.after_request
    def after_request(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Origin'] = "http://localhost"
        response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    @aplicacao.route('/')
    def index():
        # Se já estiver logado, redireciona direto para o dashboard correto
        if "usuario_logado" in session:
            user_role = session.get("tipo")
            if user_role == 'Admin':
                return redirect("/admin/dashboard")
            elif user_role == 'Escuderia':
                return redirect("/escuderia/dashboard")
            elif user_role == 'Piloto':
                return redirect("/piloto/dashboard")
            
        print('Acessou a pagina de ACESSO a aplicacao (Login F1)...')
        # Captura erro de login se houver na query string
        has_error = request.args.get("error") == "1"
        return render_template('login.html', has_error=has_error)

    @aplicacao.route('/validaBDUsuarios', methods=['POST'])
    def valida_bd_usuarios():
        return usuario_cont.valida_acesso_usuario()()

    @aplicacao.route('/logout')
    def logout():
        """Faz logout do usuário, registrando auditoria no banco e limpando sessão/cookie"""
        userid = session.get("userid")
        if userid:
            try:
                from src.app.BD.usuarios_dao import Usuarios_dao
                from src.config.database import connection_pool
                dao = Usuarios_dao(connection_pool)
                dao.registrar_log_auditoria(userid, 'LOGOUT')
            except Exception as e:
                print(f"Erro ao registrar log de logout: {e}")
                
        session.clear()
        response = redirect("/")
        # Remove o cookie de autenticação
        response.set_cookie('auth_token', '', expires=0)
        return response

    # -------------------------------------------------------------
    # ROTAS DO ADMINISTRADOR
    # -------------------------------------------------------------
    @aplicacao.route('/admin/dashboard')
    @login_required(role='Admin')
    def admin_dashboard():
        return admin_cont.dashboard()()

    @aplicacao.route('/admin/relatorios/r1')
    @login_required(role='Admin')
    def admin_relatorio_r1():
        return admin_cont.relatorio_r1()()

    @aplicacao.route('/admin/relatorios/r2')
    @login_required(role='Admin')
    def admin_relatorio_r2():
        return admin_cont.relatorio_r2()()

    @aplicacao.route('/admin/relatorios/r3')
    @login_required(role='Admin')
    def admin_relatorio_r3():
        return admin_cont.relatorio_r3()()

    @aplicacao.route('/admin/cadastro/escuderia', methods=['GET', 'POST'])
    @login_required(role='Admin')
    def admin_cadastrar_escuderia():
        return admin_cont.cadastrar_escuderia()()

    @aplicacao.route('/admin/cadastro/piloto', methods=['GET', 'POST'])
    @login_required(role='Admin')
    def admin_cadastrar_piloto():
        return admin_cont.cadastrar_piloto()()

    # -------------------------------------------------------------
    # ROTAS DA ESCUDERIA
    # -------------------------------------------------------------
    @aplicacao.route('/escuderia/dashboard')
    @login_required(role='Escuderia')
    def escuderia_dashboard():
        return escuderia_cont.dashboard()()

    @aplicacao.route('/escuderia/relatorios')
    @login_required(role='Escuderia')
    def escuderia_relatorios():
        return escuderia_cont.relatorios()()

    @aplicacao.route('/escuderia/consulta/piloto')
    @login_required(role='Escuderia')
    def escuderia_consultar_piloto():
        return escuderia_cont.consultar_piloto()()

    @aplicacao.route('/escuderia/upload/pilotos', methods=['GET', 'POST'])
    @login_required(role='Escuderia')
    def escuderia_upload_pilotos():
        return escuderia_cont.upload_pilotos()()

    # -------------------------------------------------------------
    # ROTAS DO PILOTO
    # -------------------------------------------------------------
    @aplicacao.route('/piloto/dashboard')
    @login_required(role='Piloto')
    def piloto_dashboard():
        return piloto_cont.dashboard()()

    @aplicacao.route('/piloto/relatorios')
    @login_required(role='Piloto')
    def piloto_relatorios():
        return piloto_cont.relatorios()()
