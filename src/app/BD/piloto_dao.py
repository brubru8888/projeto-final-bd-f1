"""
Módulo de Acesso a Dados (DAO) para operações do Piloto.

Conceitos de BD aplicados neste módulo:
  - Stored Functions para encapsulamento de lógica analítica no banco
  - Consultas com múltiplos JOINs para navegar pelo modelo relacional
  - ORDER BY com múltiplos critérios (DESC, ASC)
  - COALESCE para tratamento de valores NULL em agregações
  - Filtro por ponto no tempo (ORDER BY date DESC LIMIT 1)
"""


class Piloto_dao:
    """
    DAO para operações relacionadas ao perfil de Piloto.
    Encapsula todas as queries de leitura e análise de desempenho do piloto.
    """

    def __init__(self, db_pool):
        # O pool de conexões é injetado no construtor (Dependency Injection)
        self._db_pool = db_pool

    def get_years(self, driver_id):
        """
        Retorna o primeiro e último ano em que o piloto competiu.

        Conceito de BD: Stored Function com subconsultas de MIN/MAX.
        -------------------------------------------------------------
        A função 'get_piloto_years(p_driver_id)' navega pelo modelo relacional:
          results → races → seasons
        usando dois JOINs para chegar à tabela 'seasons' e obter o campo 'year'.
        MIN(year) e MAX(year) retornam a faixa temporal de participação do piloto.

        Isso demonstra como o modelo relacional normalizado exige JOINs para
        acessar atributos que ficam em tabelas associadas via FKs.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            # A função encapsula internamente: MIN(year) e MAX(year) com JOINs em races e seasons
            cursor.execute("SELECT * FROM get_piloto_years(%s)", (driver_id,))
            row = cursor.fetchone()
            cursor.close()
            if row:
                return {
                    'primeiro_ano': row[0] or 'N/A',
                    'ultimo_ano': row[1] or 'N/A'
                }
            return {'primeiro_ano': 'N/A', 'ultimo_ano': 'N/A'}
        except Exception as e:
            print(f"Erro ao buscar anos de participação do piloto {driver_id}: {e}\"")
            return {'primeiro_ano': 'N/A', 'ultimo_ano': 'N/A'}
        finally:
            # Sempre devolve a conexão ao pool, mesmo em caso de erro
            if conn:
                self._db_pool.putconn(conn)

    def get_piloto_info(self, driver_id):
        """
        Retorna nome completo e escuderia mais recente do piloto.

        Conceito de BD: Duas queries sequenciais com estratégias distintas.
        -------------------------------------------------------------------
        Query 1 — Concatenação de strings no SQL:
          'given_name || ' ' || family_name': o operador || do PostgreSQL
          concatena strings diretamente no banco, evitando concatenação no Python.
          Filtro pela PK (WHERE id = %s) garante acesso O(log n) via índice.

        Query 2 — ORDER BY + LIMIT para "último registro":
          Para descobrir a escuderia mais recente, faz JOIN em results → races
          ordenado pela data da corrida (ORDER BY rc.race_date DESC),
          e pega apenas o primeiro resultado (LIMIT 1).
          Esta técnica é equivalente a uma subconsulta com MAX(date),
          mas é mais legível e igualmente eficiente com índice em race_date.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()

            # Query 1: concatenação de nome completo diretamente no SQL
            cursor.execute("SELECT given_name || ' ' || family_name FROM drivers WHERE id = %s", (driver_id,))
            nome_piloto = cursor.fetchone()
            nome_piloto = nome_piloto[0] if nome_piloto else 'Desconhecido'

            # Query 2: busca a escuderia mais recente pelo histórico de corridas
            # JOIN: results → races (para obter race_date) → constructors (para obter nome)
            # ORDER BY race_date DESC + LIMIT 1: pega o registro mais recente
            cursor.execute('''
                SELECT c.name 
                FROM results res
                JOIN races rc ON res.race_id = rc.id
                JOIN constructors c ON res.constructor_id = c.id
                WHERE res.driver_id = %s
                ORDER BY rc.race_date DESC LIMIT 1
            ''', (driver_id,))
            escuderia_recente = cursor.fetchone()
            escuderia = escuderia_recente[0] if escuderia_recente else 'Sem Escuderia'

            cursor.close()
            return {'nome': nome_piloto, 'escuderia': escuderia}
        except Exception as e:
            print(f"Erro ao buscar info do piloto {driver_id}: {e}")
            return {'nome': 'Erro', 'escuderia': 'Erro'}
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_dashboard_details(self, driver_id):
        """
        Retorna o desempenho do piloto por ano e circuito.

        Conceito de BD: Stored Function com GROUP BY multi-coluna e CASE WHEN.
        -----------------------------------------------------------------------
        A função 'get_piloto_dashboard_details(p_driver_id)' implementa:
          - JOIN results → races → seasons → circuits (cadeia de 3 JOINs)
          - GROUP BY s.year, c.name: agrupa por (ano, circuito) — grupo composto
          - SUM(points): total de pontos do piloto naquele ano/circuito
          - SUM(CASE WHEN position = '1' THEN 1 ELSE 0 END): conta vitórias
            via expressão condicional inline (equivale a COUNT WHERE position='1')
          - COUNT(r.id): total de corridas disputadas no grupo
          - COALESCE(SUM(...), 0): substitui NULL por 0 quando não há pontos
          - ORDER BY s.year DESC, pontos DESC: ordena por ano recente primeiro,
            depois por pontos decrescente dentro do mesmo ano
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            # Invoca a função com o ID do piloto logado (vem da sessão via controller)
            cursor.execute("SELECT * FROM get_piloto_dashboard_details(%s)", (driver_id,))
            res = cursor.fetchall()
            cursor.close()
            return [{
                'ano': row[0],
                'circuito': row[1],
                # Converte Decimal do PostgreSQL para float Python para JSON/template
                'pontos': float(row[2]) if row[2] is not None else 0,
                'vitorias': row[3],
                'corridas': row[4]
            } for row in res]
        except Exception as e:
            print(f"Erro no dashboard detalhado do piloto {driver_id}: {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_r6_pontos_ano(self, driver_id):
        """
        Relatório R6: Cronologia de pontos do piloto por corrida e ano.

        Conceito de BD: Stored Function com filtro de tuplas não-nulas e ordenação temporal.
        ------------------------------------------------------------------------------------
        A função 'get_relatorio_pontos_piloto_ano(p_driver_id)' implementa:
          - JOIN results → races → seasons para obter o ano e data
          - WHERE r.points > 0: filtra apenas corridas onde o piloto pontuou
            (exclui DNF, abandonos sem pontos — reduz volume de dados retornados)
          - ORDER BY ano DESC, corrida_data ASC: ordena cronologicamente
            dentro de cada ano, do mais recente para o mais antigo entre anos

        Este relatório demonstra como filtros eficientes no banco reduzem
        o volume de dados trafegados entre banco e aplicação.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM get_relatorio_pontos_piloto_ano(%s)", (driver_id,))
            res = cursor.fetchall()
            cursor.close()
            return [{
                'ano': row[0],
                'corrida': row[1],
                'data': row[2].strftime('%d/%m/%Y') if row[2] else 'N/A',
                'pontos': float(row[3]) if row[3] is not None else 0
            } for row in res]
        except Exception as e:
            print(f"Erro no R6 do piloto {driver_id}: {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_r7_status_piloto(self, driver_id):
        """
        Relatório R7: Distribuição de status (resultados) no histórico do piloto.

        Conceito de BD: Stored Function com JOIN em tabela de domínio e GROUP BY.
        --------------------------------------------------------------------------
        A função 'get_relatorio_status_piloto(p_driver_id)' implementa:
          - JOIN results → status: decodifica o status_id (número inteiro) para
            o texto descritivo ('Finished', 'Engine', 'Accident', etc.)
          - WHERE driver_id = p_driver_id: filtra pelo piloto específico
          - GROUP BY status: agrupa todas as ocorrências do mesmo status
          - ORDER BY contagem DESC: coloca os status mais frequentes no topo

        Tabela de domínio 'status': padrão de normalização que evita armazenar
        a string de status repetidamente em cada linha de 'results'.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM get_relatorio_status_piloto(%s)", (driver_id,))
            res = cursor.fetchall()
            cursor.close()
            return [{'status': row[0], 'contagem': row[1]} for row in res]
        except Exception as e:
            print(f"Erro no R7 do piloto {driver_id}: {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)
