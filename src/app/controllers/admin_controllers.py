"""Controllers do administrador."""

from flask import render_template, request, redirect, url_for, flash
from src.app.BD.admin_dao import Admin_dao
from src.config.database import connection_pool


class AdminControllers:
    """Agrupa dashboard, relatórios e cadastros do admin."""

    def __init__(self):
        pass

    def dashboard(self):
        """Renderiza o dashboard principal."""
        def view():
            dao = Admin_dao(connection_pool)
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
        """Relatório R1."""
        def view():
            dao = Admin_dao(connection_pool)
            status_report = dao.get_r1_status_report()
            return render_template("relatorios_admin.html", active_tab="r1", status_report=status_report)
        return view

    def relatorio_r2(self):
        """Relatório R2."""
        def view():
            dao = Admin_dao(connection_pool)
            city_name = request.args.get("cidade", "").strip()
            airports = []
            if city_name:
                airports = dao.get_r2_airports_report(city_name)
            return render_template("relatorios_admin.html", active_tab="r2", airports=airports, city_name=city_name)
        return view

    def relatorio_r3(self):
        """Relatório R3."""
        def view():
            dao = Admin_dao(connection_pool)
            report_data = dao.get_r3_hierarchy_report()
            return render_template("relatorios_admin.html", active_tab="r3", report_data=report_data)
        return view

    def cadastrar_escuderia(self):
        """Cadastro de escuderia."""
        def view():
            dao = Admin_dao(connection_pool)
            if request.method == "POST":
                ref = request.form.get("constructor_ref", "").strip()
                name = request.form.get("name", "").strip()
                country_id = request.form.get("country_id")
                wiki_url = request.form.get("wikipedia_url", "").strip()

                try:
                    dao.insert_constructor(ref, name, country_id, wiki_url)
                    flash("Escuderia cadastrada com sucesso!", "success")
                    return redirect(url_for("admin_dashboard"))
                except Exception as e:
                    error_msg = str(e).split('\n')[0]
                    flash(f"Erro ao cadastrar: {error_msg}", "danger")

            countries = dao.get_countries()
            return render_template("cadastro_escuderia.html", countries=countries)
        return view

    def cadastrar_piloto(self):
        """Cadastro de piloto."""
        def view():
            dao = Admin_dao(connection_pool)
            if request.method == "POST":
                ref = request.form.get("driver_ref", "").strip()
                given_name = request.form.get("given_name", "").strip()
                family_name = request.form.get("family_name", "").strip()
                dob = request.form.get("date_of_birth")
                country_id = request.form.get("country_id")

                try:
                    dao.insert_driver(ref, given_name, family_name, dob, country_id)
                    flash("Piloto cadastrado com sucesso!", "success")
                    return redirect(url_for("admin_dashboard"))
                except Exception as e:
                    error_msg = str(e).split('\n')[0]
                    flash(f"Erro ao cadastrar: {error_msg}", "danger")

            countries = dao.get_countries()
            return render_template("cadastro_piloto.html", countries=countries)
        return view
