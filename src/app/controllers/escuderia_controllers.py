"""
Controllers da Escuderia — camada intermediária (MVC).

Funcionalidades do perfil Escuderia:
  - Dashboard: KPIs da escuderia (vitórias, pilotos, anos)
  - Relatórios R4 e R5: vitórias por piloto e status de corridas
  - Consulta de pilotos por sobrenome (busca LIKE no banco)
  - Upload em lote de pilotos via arquivo CSV (transações independentes)

Conceito de BD central deste módulo:
  - Todas as operações são filtradas pelo 'id_original' da sessão,
    que aponta para o 'id' da escuderia logada na tabela 'constructors'.
  - Isso implementa isolamento de dados: cada escuderia só vê seus próprios dados.
"""

import csv
import io
from flask import render_template, request, redirect, url_for, session, flash
from src.app.BD.escuderia_dao import Escuderia_dao
from src.app.BD.admin_dao import Admin_dao
from src.config.database import connection_pool


class EscuderiaControllers:
    """
    Controller para todas as funcionalidades do perfil Escuderia.
    
    A sessão Flask armazena o 'id_original' após o login — esse valor
    corresponde à coluna 'id' da tabela 'constructors' no banco.
    Todas as consultas usam esse ID para filtrar dados da escuderia logada.
    """

    def __init__(self):
        pass

    def dashboard(self):
        """
        Renderiza o dashboard da Escuderia com KPIs.

        Isolamento de dados via sessão:
          session.get("id_original") retorna o ID da escuderia logada.
          Todas as queries são filtradas por esse ID, garantindo que
          cada escuderia acesse apenas seus próprios dados.
        """
        def view():
            dao = Escuderia_dao(connection_pool)
            # ID da escuderia logada — armazenado na sessão no momento do login
            constructor_id = session.get("id_original")

            # Chama a stored function filtrada pelo ID da escuderia
            stats = dao.get_dashboard(constructor_id)
            info_user = dao.get_escuderia_info(constructor_id)
            return render_template("dashboard_escuderia.html", stats=stats, info_user=info_user)
        return view

    def relatorios(self):
        """
        Renderiza os relatórios R4 e R5 da Escuderia.

        R4: Vitórias por piloto — via stored function get_relatorio_vitorias_pilotos()
        R5: Status de corridas — via stored function get_relatorio_status_escuderia()
        
        Ambas as funções recebem o constructor_id como parâmetro e filtram
        resultados para a escuderia específica logada.
        """
        def view():
            dao = Escuderia_dao(connection_pool)
            constructor_id = session.get("id_original")

            # Consultas paralelas ao banco: cada chamada usa uma conexão do pool
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
        """
        Consulta pilotos da escuderia por sobrenome (busca parcial).

        Conceito de BD: Busca com LIKE filtrada por FK.
        -----------------------------------------------
        O parâmetro 'sobrenome' da query string é passado ao DAO que
        executa uma query com LIKE '%termo%' e filtro por constructor_id.
        A busca só é realizada se o parâmetro for fornecido (evita
        carregar TODOS os pilotos da escuderia desnecessariamente).
        """
        def view():
            dao = Escuderia_dao(connection_pool)
            constructor_id = session.get("id_original")
            # Parâmetro vem da URL: /escuderia/consulta/piloto?sobrenome=Hamilton
            sobrenome = request.args.get("sobrenome", "").strip()
            pilotos = []

            if sobrenome:
                # Só executa a query se o usuário digitou um sobrenome
                pilotos = dao.search_drivers_by_family_name(sobrenome, constructor_id)

            stats = dao.get_dashboard(constructor_id)
            info_user = dao.get_escuderia_info(constructor_id)

            return render_template("consulta_piloto.html", pilotos=pilotos, sobrenome=sobrenome, stats=stats, info_user=info_user)
        return view

    def upload_pilotos(self):
        """
        Upload em lote de pilotos via arquivo CSV com transações independentes.

        Conceito de BD: Bulk Insert com Transações Isoladas por Registro.
        ------------------------------------------------------------------
        O arquivo CSV pode conter múltiplos pilotos. Para cada linha:
          1. Lê os dados da linha (driver_ref, given_name, family_name, dob, country_id)
          2. Chama insert_driver_independent_transaction() no DAO
          3. Cada INSERT é uma transação separada:
             - Se falhar (duplicado, FK inválida, etc.): registra na lista 'falhas'
             - Se suceder: registra na lista 'sucessos'
          4. O processamento continua independentemente do resultado de cada linha

        Esta estratégia implementa o conceito de "partial success" no bulk insert:
        erros em linhas individuais não afetam o processamento das demais.
        
        Ao inserir via DAO, os Triggers do PostgreSQL são disparados:
          - BEFORE: verifica login duplicado na tabela USERS
          - AFTER: cria usuário do tipo 'Piloto' em USERS automaticamente

        O arquivo é lido em memória usando io.StringIO (sem salvar em disco),
        o que é eficiente e seguro para arquivos de tamanho moderado.
        """
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

                # Listas para acumular resultados de sucesso e falha
                sucessos = []
                falhas = []

                try:
                    # Decodifica o arquivo binário para texto UTF-8 em memória
                    # io.StringIO evita salvar o arquivo em disco
                    stream = io.StringIO(file.stream.read().decode("utf-8"), newline=None)
                    csv_reader = csv.reader(stream)

                    # Flag para detectar e ignorar o cabeçalho do CSV (se existir)
                    header_checked = False

                    for row in csv_reader:
                        # Ignora linhas vazias ou com menos colunas que o esperado
                        if not row or len(row) < 5:
                            continue

                        # Verifica se a primeira linha é um cabeçalho textual
                        if not header_checked:
                            header_checked = True
                            if "driver_ref" in row[0].lower() or "given_name" in row[1].lower():
                                continue  # Pula o cabeçalho e processa a próxima linha

                        # Extrai os campos do CSV (ordem: ref, nome, sobrenome, data, país)
                        ref = row[0].strip()
                        given_name = row[1].strip()
                        family_name = row[2].strip()
                        dob = row[3].strip()
                        country_id = row[4].strip()

                        # Transação independente: falha nesta linha não afeta as demais
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

                    # Exibe página de resultados com listas de sucesso e falha
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

            # GET: exibe formulário de upload
            return render_template("upload_pilotos.html", stats=stats, info_user=info_user)
        return view
