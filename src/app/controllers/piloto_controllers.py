"""Controllers do piloto."""

from flask import render_template, session, redirect
from src.app.BD.piloto_dao import Piloto_dao
from src.config.database import connection_pool


class PilotoControllers:
    """Dashboard e relatórios do piloto."""

    def __init__(self):
        pass

    def dashboard(self):
        """Renderiza o dashboard do piloto."""
        def view():
            driver_id = session.get('id_original')
            if not driver_id:
                return redirect('/')

            dao = Piloto_dao(connection_pool)
            try:
                years = dao.get_years(driver_id)
                details = dao.get_dashboard_details(driver_id)
                info_user = dao.get_piloto_info(driver_id)
                return render_template(
                    "dashboard_piloto.html",
                    years=years,
                    details=details,
                    info_user=info_user
                )
            except Exception as e:
                print(f"Erro no controller piloto: {e}")
                return render_template(
                    "dashboard_piloto.html",
                    years={'primeiro_ano': 'N/A', 'ultimo_ano': 'N/A'},
                    details=[],
                    info_user={'nome': 'Desconhecido', 'escuderia': 'Desconhecida'}
                )
        return view

    def relatorios(self):
        """Renderiza os relatórios R6 e R7."""
        def view():
            dao = Piloto_dao(connection_pool)
            driver_id = session.get("id_original")

            r6_data = dao.get_r6_pontos_ano(driver_id)
            r7_data = dao.get_r7_status_piloto(driver_id)
            info_user = dao.get_piloto_info(driver_id)

            return render_template(
                "relatorios_piloto.html",
                r6_data=r6_data,
                r7_data=r7_data,
                info_user=info_user
            )
        return view
