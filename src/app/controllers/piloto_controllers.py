from flask import render_template, session
from src.app.BD.piloto_dao import Piloto_dao
from src.config.database import connection_pool

class PilotoControllers:
    def __init__(self):
        pass

    def dashboard(self):
        def view():
            dao = Piloto_dao(connection_pool)
            driver_id = session.get("id_original")
            
            years = dao.get_years(driver_id)
            details = dao.get_dashboard_details(driver_id)
            
            return render_template(
                "dashboard_piloto.html", 
                years=years, 
                details=details
            )
        return view

    def relatorios(self):
        def view():
            dao = Piloto_dao(connection_pool)
            driver_id = session.get("id_original")
            
            r6_data = dao.get_r6_pontos_ano(driver_id)
            r7_data = dao.get_r7_status_piloto(driver_id)
            
            return render_template(
                "relatorios_piloto.html", 
                r6_data=r6_data, 
                r7_data=r7_data
            )
        return view
