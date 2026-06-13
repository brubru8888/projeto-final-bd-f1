"""Controllers da escuderia."""

import csv
import io
from flask import render_template, request, redirect, url_for, session, flash
from src.app.BD.escuderia_dao import Escuderia_dao
from src.app.BD.admin_dao import Admin_dao
from src.config.database import connection_pool


class EscuderiaControllers:
    """Dashboard, relatórios, consulta e upload em lote."""

    def __init__(self):
        pass

    def dashboard(self):
        """Renderiza o dashboard da escuderia."""
        def view():
            dao = Escuderia_dao(connection_pool)
            constructor_id = session.get("id_original")
            stats = dao.get_dashboard(constructor_id)
            info_user = dao.get_escuderia_info(constructor_id)
            return render_template("dashboard_escuderia.html", stats=stats, info_user=info_user)
        return view

    def relatorios(self):
        """Renderiza os relatórios R4 e R5."""
        def view():
            dao = Escuderia_dao(connection_pool)
            constructor_id = session.get("id_original")
            r4_data = dao.get_r4_vitorias_pilotos(constructor_id)
            r5_data = dao.get_r5_status_escuderia(constructor_id)
            stats = dao.get_dashboard(constructor_id)
            info_user = dao.get_escuderia_info(constructor_id)

            return render_template(
                "relatorios_escuderia.html",
                r4_data=r4_data,
                r5_data=r5_data,
                stats=stats,
                info_user=info_user
            )
        return view

    def consultar_piloto(self):
        """Consulta pilotos por sobrenome."""
        def view():
            dao = Escuderia_dao(connection_pool)
            constructor_id = session.get("id_original")
            sobrenome = request.args.get("sobrenome", "").strip()
            pilotos = []

            if sobrenome:
                pilotos = dao.search_drivers_by_family_name(sobrenome, constructor_id)

            stats = dao.get_dashboard(constructor_id)
            info_user = dao.get_escuderia_info(constructor_id)

            return render_template("consulta_piloto.html", pilotos=pilotos, sobrenome=sobrenome, stats=stats, info_user=info_user)
        return view

    def upload_pilotos(self):
        """Upload em lote de pilotos via CSV."""
        def view():
            dao = Escuderia_dao(connection_pool)
            admin_dao = Admin_dao(connection_pool)
            constructor_id = session.get("id_original")
            stats = dao.get_dashboard(constructor_id)
            info_user = dao.get_escuderia_info(constructor_id)

            if request.method == "POST":
                file = request.files.get("file")
                if not file or file.filename == "":
                    flash("Por favor, selecione um arquivo válido para upload.", "danger")
                    return redirect(request.url)

                sucessos = []
                falhas = []

                try:
                    stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
                    csv_reader = csv.reader(stream)

                    header_checked = False

                    for row in csv_reader:
                        if not row or len(row) < 5:
                            continue

                        if not header_checked:
                            header_checked = True
                            if "driver_ref" in row[0].lower() or "given_name" in row[1].lower():
                                continue

                        ref = row[0].strip()
                        given_name = row[1].strip()
                        family_name = row[2].strip()
                        dob = row[3].strip()
                        country_id = row[4].strip()

                        success, msg = dao.insert_driver_independent_transaction(
                            ref, given_name, family_name, dob, country_id
                        )

                        info = {
                            'ref': ref,
                            'nome': f"{given_name} {family_name}",
                            'dob': dob,
                            'country_id': country_id
                        }

                        if success:
                            sucessos.append(info)
                        else:
                            info['erro'] = msg
                            falhas.append(info)

                    return render_template(
                        "upload_resultados.html",
                        sucessos=sucessos,
                        falhas=falhas,
                        stats=stats,
                        info_user=info_user
                    )

                except Exception as e:
                    flash(f"Erro ao processar o arquivo: {e}", "danger")
                    return redirect(request.url)

            return render_template("upload_pilotos.html", stats=stats, info_user=info_user)
        return view
