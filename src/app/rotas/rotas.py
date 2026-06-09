"""
Módulo de definição de rotas da aplicação Flask.

Conceito de Roteamento e Controle de Acesso:
---------------------------------------------
Este módulo registra todas as URLs (endpoints) da aplicação e associa
cada uma ao controller correspondente. O decorator @login_required
implementa controle de acesso antes da execução do controller.

Estrutura de URLs por perfil:
  /                       → Página de login (pública)
  /validaBDUsuarios       → POST de autenticação (pública)
  /logout                 → Encerra sessão e registra auditoria no BD
  /admin/*                → Exclusivo para tipo='Admin'
  /escuderia/*            → Exclusivo para tipo='Escuderia'
  /piloto/*               → Exclusivo para tipo='Piloto'

O decorator @login_required(role='X') verifica:
  1. Se o usuário está autenticado (sessão + cookie válidos)
  2. Se o campo 'tipo' do banco corresponde ao role exigido pela rota
"""

from src.app.controllers.usuarios_controllers import UsuariosControllers
from src.app.controllers.admin_controllers import AdminControllers
from src.app.controllers.escuderia_controllers import EscuderiaControllers
from src.app.controllers.piloto_controllers import PilotoControllers
from src.app.controllers.auth import login_required
from flask import render_template, session, redirect, request

# Instâncias globais dos controllers — criadas uma única vez (Singleton implícito)
usuario_cont = UsuariosControllers()
admin_cont = AdminControllers()
escuderia_cont = EscuderiaControllers()
piloto_cont = PilotoControllers()


def rotas(aplicacao):
    """
    Registra todas as rotas da aplicação Flask.
    
    O Flask usa decorators @aplicacao.route() para mapear URLs para funções.
    Cada função de rota chama o controller correspondente e retorna a resposta HTTP.
    """

    # -------------------------------------------------------------------
    # Configuração de CORS (Cross-Origin Resource Sharing)
    # Necessário para permitir que o frontend faça requisições ao backend
    # mesmo quando servidos de origens diferentes (desenvolvimento local)
    # -------------------------------------------------------------------
    @aplicacao.after_request
    def after_request(response):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Origin'] = "http://localhost"
        response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    # -------------------------------------------------------------------
    # ROTA PÚBLICA: Página de login
    # Redireciona usuários já autenticados para seu dashboard correspondente
    # (campo 'tipo' da sessão determina a URL de destino — RBAC)
    # -------------------------------------------------------------------
    @aplicacao.route('/')
    def index():
        # Se há usuário na sessão, redireciona para o dashboard do seu perfil
        # (evita mostrar o login novamente para quem já está autenticado)
        if "usuario_logado" in session:
            user_role = session.get("tipo")
            if user_role == 'Admin':
                return redirect("/admin/dashboard")
            elif user_role == 'Escuderia':
                return redirect("/escuderia/dashboard")
            elif user_role == 'Piloto':
                return redirect("/piloto/dashboard")

        print('Acessou a pagina de ACESSO a aplicacao (Login F1)...')
        # Exibe mensagem de erro de login se ?error=1 estiver na URL
        has_error = request.args.get("error") == "1"
        return render_template('login.html', has_error=has_error)

    # -------------------------------------------------------------------
    # ROTA DE AUTENTICAÇÃO: Processa o formulário de login
    # POST /validaBDUsuarios → valida credenciais no banco → cria sessão
    # -------------------------------------------------------------------
    @aplicacao.route('/validaBDUsuarios', methods=['POST'])
    def valida_bd_usuarios():
        return usuario_cont.valida_acesso_usuario()()

    # -------------------------------------------------------------------
    # ROTA DE LOGOUT: Encerra sessão e registra auditoria no banco
    # Conceito: INSERT em USERS_LOG com action='LOGOUT' antes de limpar sessão
    # -------------------------------------------------------------------
    @aplicacao.route('/logout')
    def logout():
        """Encerra a sessão do usuário, registra LOGOUT na auditoria e limpa cookies."""
        userid = session.get("userid")
        if userid:
            try:
                # Registra a ação de LOGOUT na tabela USERS_LOG antes de limpar a sessão
                # (depois de session.clear(), não temos mais acesso ao userid)
                from src.app.BD.usuarios_dao import Usuarios_dao
                from src.config.database import connection_pool
                dao = Usuarios_dao(connection_pool)
                dao.registrar_log_auditoria(userid, 'LOGOUT')
            except Exception as e:
                print(f"Erro ao registrar log de logout: {e}")

        # Limpa todos os dados da sessão server-side
        session.clear()
        response = redirect("/")
        # Remove o cookie de autenticação definindo expires=0 (expirado imediatamente)
        response.set_cookie('auth_token', '', expires=0)
        return response

    # -------------------------------------------------------------------
    # ROTAS DO ADMINISTRADOR
    # Todas protegidas com @login_required(role='Admin')
    # O decorator verifica sessão + token + tipo='Admin' antes de executar
    # -------------------------------------------------------------------
    @aplicacao.route('/admin/dashboard')
    @login_required(role='Admin')
    def admin_dashboard():
        """Dashboard admin: estatísticas gerais + dados da última temporada."""
        return admin_cont.dashboard()()

    @aplicacao.route('/admin/relatorios/r1')
    @login_required(role='Admin')
    def admin_relatorio_r1():
        """R1: Distribuição de resultados por status (via VIEW vw_relatorio_status)."""
        return admin_cont.relatorio_r1()()

    @aplicacao.route('/admin/relatorios/r2')
    @login_required(role='Admin')
    def admin_relatorio_r2():
        """R2: Aeroportos próximos a uma cidade (via stored function com Haversine)."""
        return admin_cont.relatorio_r2()()

    @aplicacao.route('/admin/relatorios/r3')
    @login_required(role='Admin')
    def admin_relatorio_r3():
        """R3: Hierarquia Circuitos → Corridas (via duas VIEWs + query inline)."""
        return admin_cont.relatorio_r3()()

    @aplicacao.route('/admin/cadastro/escuderia', methods=['GET', 'POST'])
    @login_required(role='Admin')
    def admin_cadastrar_escuderia():
        """Cadastro de escuderia: INSERT em 'constructors' + trigger AFTER cria usuário."""
        return admin_cont.cadastrar_escuderia()()

    @aplicacao.route('/admin/cadastro/piloto', methods=['GET', 'POST'])
    @login_required(role='Admin')
    def admin_cadastrar_piloto():
        """Cadastro de piloto: INSERT em 'drivers' + trigger AFTER cria usuário."""
        return admin_cont.cadastrar_piloto()()

    # -------------------------------------------------------------------
    # ROTAS DA ESCUDERIA
    # Todas protegidas com @login_required(role='Escuderia')
    # As queries no banco são filtradas pelo id_original da sessão
    # -------------------------------------------------------------------
    @aplicacao.route('/escuderia/dashboard')
    @login_required(role='Escuderia')
    def escuderia_dashboard():
        """Dashboard da escuderia: KPIs via stored function get_escuderia_dashboard()."""
        return escuderia_cont.dashboard()()

    @aplicacao.route('/escuderia/relatorios')
    @login_required(role='Escuderia')
    def escuderia_relatorios():
        """R4 (vitórias por piloto) e R5 (status de corridas) da escuderia logada."""
        return escuderia_cont.relatorios()()

    @aplicacao.route('/escuderia/consulta/piloto')
    @login_required(role='Escuderia')
    def escuderia_consultar_piloto():
        """Busca de pilotos da escuderia por sobrenome (LIKE case-insensitive no banco)."""
        return escuderia_cont.consultar_piloto()()

    @aplicacao.route('/escuderia/upload/pilotos', methods=['GET', 'POST'])
    @login_required(role='Escuderia')
    def escuderia_upload_pilotos():
        """Upload CSV de pilotos: bulk insert com transações independentes por linha."""
        return escuderia_cont.upload_pilotos()()

    # -------------------------------------------------------------------
    # ROTAS DO PILOTO
    # Todas protegidas com @login_required(role='Piloto')
    # As queries no banco são filtradas pelo id_original (drivers.id) da sessão
    # -------------------------------------------------------------------
    @aplicacao.route('/piloto/dashboard')
    @login_required(role='Piloto')
    def piloto_dashboard():
        """Dashboard do piloto: anos de participação + desempenho por circuito/ano."""
        return piloto_cont.dashboard()()

    @aplicacao.route('/piloto/relatorios')
    @login_required(role='Piloto')
    def piloto_relatorios():
        """R6 (pontos por corrida) e R7 (distribuição de status) do piloto logado."""
        return piloto_cont.relatorios()()
