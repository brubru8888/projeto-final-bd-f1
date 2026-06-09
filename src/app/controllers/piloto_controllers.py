"""
Controllers do Piloto — camada intermediária (MVC).

Funcionalidades do perfil Piloto:
  - Dashboard: KPIs de desempenho (anos de participação, pontos, vitórias por circuito)
  - Relatórios R6 e R7: pontos por ano/corrida e status do histórico

Conceito de BD:
  - O 'id_original' da sessão aponta para o 'id' na tabela 'drivers'.
  - Todas as consultas são parametrizadas por esse ID, garantindo que
    cada piloto acesse apenas seus próprios dados (isolamento de dados).
"""

from flask import render_template, session
from src.app.BD.piloto_dao import Piloto_dao
from src.config.database import connection_pool


class PilotoControllers:
    """
    Controller para todas as funcionalidades do perfil Piloto.

    A sessão Flask armazena o 'id_original' após o login — esse valor
    corresponde à coluna 'id' da tabela 'drivers' no banco de dados.
    """

    def __init__(self):
        pass

    def dashboard(self):
        """
        Renderiza o dashboard do Piloto com dados de desempenho.

        Fluxo de dados:
          1. Obtém driver_id da sessão (armazenado no login)
          2. Chama get_years(): MIN/MAX de ano via stored function
          3. Chama get_dashboard_details(): desempenho por ano e circuito
             via stored function com GROUP BY e CASE WHEN
          4. Chama get_piloto_info(): nome e escuderia atual
          5. Renderiza o template com todos os dados

        Tratamento de erro: em caso de falha no banco, renderiza o
        template com valores padrão (não exibe erro genérico ao usuário).
        """
        def view():
            # Recupera o ID do piloto logado da sessão server-side
            driver_id = session.get('id_original')
            if not driver_id:
                return redirect('/login')

            dao = Piloto_dao(connection_pool)
            try:
                # Consulta 1: intervalo de anos de participação (MIN/MAX via stored function)
                years = dao.get_years(driver_id)
                # Consulta 2: desempenho por ano e circuito (GROUP BY + CASE WHEN)
                details = dao.get_dashboard_details(driver_id)
                # Consulta 3: nome completo e escuderia mais recente (ORDER BY date DESC LIMIT 1)
                info_user = dao.get_piloto_info(driver_id)
                return render_template(
                    "dashboard_piloto.html",
                    years=years,
                    details=details,
                    info_user=info_user
                )
            except Exception as e:
                print(f"Erro no controller piloto: {e}")
                # Graceful degradation: exibe dashboard com valores padrão em caso de erro
                return render_template(
                    "dashboard_piloto.html",
                    years={'primeiro_ano': 'N/A', 'ultimo_ano': 'N/A'},
                    details=[],
                    info_user={'nome': 'Desconhecido', 'escuderia': 'Desconhecida'}
                )
        return view

    def relatorios(self):
        """
        Renderiza os relatórios R6 e R7 do Piloto.

        R6: Pontos por corrida e ano — via stored function get_relatorio_pontos_piloto_ano()
            Filtra WHERE points > 0 (apenas corridas pontuadas) e ordena por ano DESC.

        R7: Status das corridas — via stored function get_relatorio_status_piloto()
            JOIN results → status + GROUP BY para distribuição de resultados.

        Ambas as funções recebem o driver_id como parâmetro, garantindo
        que o piloto acesse apenas seus próprios dados históricos.
        """
        def view():
            dao = Piloto_dao(connection_pool)
            # ID do piloto logado — armazenado na sessão durante o login
            driver_id = session.get("id_original")

            # Dados do R6: pontos por ano e corrida (filtro WHERE points > 0)
            r6_data = dao.get_r6_pontos_ano(driver_id)
            # Dados do R7: distribuição de status (JOIN com tabela de domínio 'status')
            r7_data = dao.get_r7_status_piloto(driver_id)
            # Info do usuário para o cabeçalho da página
            info_user = dao.get_piloto_info(driver_id)

            return render_template(
                "relatorios_piloto.html",
                r6_data=r6_data,
                r7_data=r7_data,
                info_user=info_user
            )
        return view
