"""
Controllers do Administrador — camada intermediária (MVC).

Padrão MVC (Model-View-Controller):
  - Model: os DAOs (Admin_dao, etc.) que acessam o banco de dados
  - View: os templates HTML (Jinja2) em src/app/views/templates/
  - Controller: este módulo — coordena Model e View sem lógica de BD direta

Responsabilidades deste módulo:
  - Receber requisições HTTP (via rotas definidas em rotas.py)
  - Chamar o DAO apropriado para buscar/inserir dados no banco
  - Passar os dados obtidos para o template correto via render_template()
  - Tratar formulários POST (cadastro de escuderias e pilotos)
  - Exibir mensagens de feedback (flash messages) ao usuário
"""

from flask import render_template, request, redirect, url_for, flash
from src.app.BD.admin_dao import Admin_dao
from src.config.database import connection_pool


class AdminControllers:
    """
    Controller para todas as funcionalidades do perfil Administrador.
    
    Cada método retorna uma função 'view' interna — isso permite que o
    mesmo controller seja chamado por múltiplas rotas com assinaturas diferentes.
    """

    def __init__(self):
        pass

    def dashboard(self):
        """
        Renderiza o dashboard principal do Administrador.
        
        Fluxo: Rota GET /admin/dashboard → controller → DAO → banco → template
        Dados carregados:
          - stats: contagens gerais (pilotos, escuderias, corridas, etc.)
          - corridas_recentes: corridas da última temporada (via stored function)
          - escuderias_recentes: ranking de escuderias (via stored function)
          - pilotos_recentes: ranking de pilotos (via stored function)
        """
        def view():
            # Instancia o DAO com o pool de conexões compartilhado
            dao = Admin_dao(connection_pool)
            # Cada chamada ao DAO usa uma conexão do pool, executa a query
            # e devolve a conexão — operações independentes e atômicas
            stats = dao.get_dashboard_stats()
            corridas_recentes = dao.get_dashboard_corridas_recentes()
            escuderias_recentes = dao.get_dashboard_escuderias_recentes()
            pilotos_recentes = dao.get_dashboard_pilotos_recentes()
            return render_template(
                "dashboard_admin.html",
                stats=stats,
                corridas_recentes=corridas_recentes,
                escuderias_recentes=escuderias_recentes,
                pilotos_recentes=pilotos_recentes
            )
        return view

    def relatorio_r1(self):
        """
        Relatório R1: Distribuição de resultados por status.
        Lê da VIEW 'vw_relatorio_status' via Admin_dao.get_r1_status_report().
        """
        def view():
            dao = Admin_dao(connection_pool)
            # Consulta a view vw_relatorio_status (encapsula JOIN + GROUP BY)
            status_report = dao.get_r1_status_report()
            return render_template("relatorios_admin.html", active_tab="r1", status_report=status_report)
        return view

    def relatorio_r2(self):
        """
        Relatório R2: Aeroportos próximos a uma cidade.
        
        Conceito: parâmetro da query string (?cidade=Sao+Paulo) é passado
        para a stored function do banco, que calcula distâncias Haversine.
        Apenas executa a busca se o parâmetro 'cidade' foi fornecido (GET form).
        """
        def view():
            dao = Admin_dao(connection_pool)
            # Parâmetro vem da query string da URL: /admin/relatorios/r2?cidade=Nome
            city_name = request.args.get("cidade", "").strip()
            airports = []
            if city_name:
                # Só chama o banco se o usuário forneceu uma cidade para pesquisar
                airports = dao.get_r2_airports_report(city_name)
            return render_template("relatorios_admin.html", active_tab="r2", airports=airports, city_name=city_name)
        return view

    def relatorio_r3(self):
        """
        Relatório R3: Hierarquia Circuitos → Corridas → Escuderias.
        Combina duas views e uma query inline no DAO para gerar estrutura hierárquica.
        """
        def view():
            dao = Admin_dao(connection_pool)
            report_data = dao.get_r3_hierarchy_report()
            return render_template("relatorios_admin.html", active_tab="r3", report_data=report_data)
        return view

    def cadastrar_escuderia(self):
        """
        Formulário de cadastro de nova escuderia (GET) e processamento (POST).

        Conceito de BD: Transação DML com feedback de erro de constraint.
        -----------------------------------------------------------------
        No POST: os dados do formulário são passados para o DAO que executa
        um INSERT na tabela 'constructors'. O PostgreSQL pode lançar exceções
        em caso de violação de constraints (ex: constructor_ref duplicado,
        FK inválida para country_id). Essas exceções são capturadas e
        exibidas ao usuário via flash message.

        O 'flash' do Flask armazena a mensagem na sessão e a exibe na
        próxima requisição — útil para mensagens pós-redirect.
        """
        def view():
            dao = Admin_dao(connection_pool)
            if request.method == "POST":
                # Coleta dados do formulário HTML (campos name="" do <input>)
                ref = request.form.get("constructor_ref", "").strip()
                name = request.form.get("name", "").strip()
                country_id = request.form.get("country_id")
                wiki_url = request.form.get("wikipedia_url", "").strip()

                try:
                    # O DAO executa INSERT + COMMIT; triggers são disparados automaticamente
                    dao.insert_constructor(ref, name, country_id, wiki_url)
                    flash("Escuderia cadastrada com sucesso!", "success")
                    return redirect(url_for("admin_dashboard"))
                except Exception as e:
                    # Extrai apenas a primeira linha da mensagem de erro do PostgreSQL
                    error_msg = str(e).split('\n')[0]
                    flash(f"Erro ao cadastrar: {error_msg}", "danger")

            # GET: carrega lista de países para o select do formulário
            countries = dao.get_countries()
            return render_template("cadastro_escuderia.html", countries=countries)
        return view

    def cadastrar_piloto(self):
        """
        Formulário de cadastro de novo piloto (GET) e processamento (POST).

        Conceito de BD: INSERT com Triggers em cascata.
        ------------------------------------------------
        O INSERT em 'drivers' dispara automaticamente:
          1. Trigger BEFORE: verifica duplicidade de login em USERS
          2. Trigger AFTER: cria registro em USERS com login=driver_ref+'_d'
        Se o trigger BEFORE lançar exceção, o INSERT é revertido e
        a mensagem de erro do trigger é capturada e exibida ao usuário.
        """
        def view():
            dao = Admin_dao(connection_pool)
            if request.method == "POST":
                ref = request.form.get("driver_ref", "").strip()
                given_name = request.form.get("given_name", "").strip()
                family_name = request.form.get("family_name", "").strip()
                dob = request.form.get("date_of_birth")
                country_id = request.form.get("country_id")

                try:
                    # INSERT dispara triggers BEFORE e AFTER definidos no SQL
                    dao.insert_driver(ref, given_name, family_name, dob, country_id)
                    flash("Piloto cadastrado com sucesso!", "success")
                    return redirect(url_for("admin_dashboard"))
                except Exception as e:
                    error_msg = str(e).split('\n')[0]
                    flash(f"Erro ao cadastrar: {error_msg}", "danger")

            # GET: carrega países para o select do formulário
            countries = dao.get_countries()
            return render_template("cadastro_piloto.html", countries=countries)
        return view
