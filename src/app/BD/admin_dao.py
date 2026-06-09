"""
Módulo de Acesso a Dados (DAO) para operações administrativas.

Padrão de Projeto: DAO (Data Access Object)
--------------------------------------------
O padrão DAO encapsula toda a lógica de acesso ao banco de dados em uma
classe separada. Isso garante:
  - Separação de responsabilidades: a lógica de negócio (controller) não
    se mistura com queries SQL.
  - Facilidade de manutenção: para mudar uma consulta, basta alterar o DAO.
  - Reutilização: o mesmo DAO pode ser usado por múltiplos controllers.

Conceitos de BD aplicados neste módulo:
  - Consultas simples (SELECT com COUNT, ORDER BY, LIMIT)
  - Transações com COMMIT e ROLLBACK (INSERT)
  - Invocação de Stored Functions via SELECT * FROM funcao()
  - Consulta de Views (vw_relatorio_*)
  - JOINs e agregações (GROUP BY, COUNT, AVG, MIN, MAX)
  - Tratamento de exceções e gerenciamento do pool de conexões
"""


class Admin_dao:
    """
    DAO responsável por todas as consultas do perfil Administrador.
    Recebe o pool de conexões no construtor e o usa para todas as operações.
    """

    def __init__(self, db_pool):
        # O pool de conexões é injetado (Dependency Injection), permitindo
        # reutilização e testabilidade.
        self._db_pool = db_pool

    def get_dashboard_stats(self):
        """
        Retorna contagens gerais para o dashboard do administrador.

        Conceito de BD: Consultas agregadas simples (SELECT COUNT(*)).
        Cada COUNT(*) executa um Full Table Scan ou usa um índice para
        retornar a quantidade de linhas de uma tabela. Estas são consultas
        de leitura puras — sem modificação de dados.

        Uso do Pool: getconn() / putconn() no bloco finally garante que
        a conexão sempre é devolvida ao pool, mesmo em caso de erro.
        """
        conn = None
        try:
            # Obtém uma conexão disponível do pool
            conn = self._db_pool.getconn()
            cursor = conn.cursor()

            # Consultas de agregação: contam o total de registros em cada tabela principal
            cursor.execute("SELECT COUNT(*) FROM drivers")
            pilotos = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM constructors")
            escuderias = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM races")
            corridas = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM circuits")
            circuitos = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM seasons")
            temporadas = cursor.fetchone()[0]

            # ORDER BY DESC + LIMIT 1: busca o registro mais recente sem subconsulta
            cursor.execute("SELECT year FROM seasons ORDER BY year DESC LIMIT 1")
            row = cursor.fetchone()
            temporada_recente = row[0] if row else 'N/A'

            cursor.close()
            return {
                'pilotos': pilotos,
                'escuderias': escuderias,
                'corridas': corridas,
                'circuitos': circuitos,
                'temporadas': temporadas,
                'temporada_recente': temporada_recente
            }
        except Exception as e:
            print(f"Erro ao obter estatísticas admin: {e}")
            return {'pilotos': 0, 'escuderias': 0, 'corridas': 0, 'circuitos': 0, 'temporadas': 0, 'temporada_recente': 'N/A'}
        finally:
            # O bloco 'finally' garante que a conexão é SEMPRE devolvida ao pool,
            # independentemente de sucesso ou erro — evita "connection leaks".
            if conn:
                self._db_pool.putconn(conn)

    def get_countries(self):
        """
        Retorna a lista de todos os países ordenada por nome.

        Conceito de BD: SELECT simples com ORDER BY.
        ORDER BY ASC garante que os resultados venham em ordem alfabética
        crescente, facilitando o preenchimento de selects (dropdowns) na UI.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            # ORDER BY garante ordenação no servidor do banco, mais eficiente
            # do que ordenar no código Python após buscar.
            cursor.execute("SELECT id, name FROM countries ORDER BY name ASC")
            res = cursor.fetchall()
            cursor.close()
            # Converte os resultados (lista de tuplas) em lista de dicionários
            # para facilitar o uso nos templates Jinja2
            return [{'id': row[0], 'name': row[1]} for row in res]
        except Exception as e:
            print(f"Erro ao obter países: {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def insert_constructor(self, ref, name, country_id, wiki_url):
        """
        Cadastra uma nova escuderia no banco de dados.

        Conceito de BD: Transação com DML (INSERT) e controle explícito de transação.
        -------------------------------------------------------------------------------
        O PostgreSQL opera no modo "autocommit = OFF" por padrão via psycopg2,
        ou seja, toda operação DML (INSERT, UPDATE, DELETE) precisa de um
        COMMIT explícito para ser persistida.

        - conn.commit(): confirma a transação, tornando o INSERT permanente.
        - conn.rollback(): desfaz a transação em caso de erro, garantindo
          que o banco não fique em estado inconsistente (princípio da Atomicidade).

        O uso de parâmetros (%s) evita SQL Injection — o psycopg2 faz o
        escape correto dos valores antes de enviar ao banco.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            # Parâmetros passados como tupla — o psycopg2 os escapa automaticamente
            cursor.execute(
                """
                INSERT INTO constructors (constructor_ref, name, country_id, wikipedia_url)
                VALUES (%s, %s, %s, %s)
                """,
                (ref, name, country_id, wiki_url or None)
            )
            # COMMIT: persiste a transação no banco de dados
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            if conn:
                # ROLLBACK: desfaz qualquer alteração parcial em caso de erro
                conn.rollback()
            print(f"Erro ao cadastrar escuderia: {e}")
            raise e
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def insert_driver(self, ref, given_name, family_name, dob, country_id):
        """
        Cadastra um novo piloto no banco de dados.

        Conceito de BD: INSERT com Triggers associados.
        ------------------------------------------------
        Ao executar este INSERT na tabela 'drivers', dois triggers
        definidos no SQL são disparados automaticamente pelo PostgreSQL:
          1. BEFORE INSERT: trg_drivers_before_insert_update
             → Verifica se já existe um usuário com o login gerado (driver_ref + '_d')
             → Se sim, levanta uma exceção, impedindo o INSERT
          2. AFTER INSERT: trg_drivers_after_insert_update
             → Cria automaticamente um registro na tabela USERS para o novo piloto
             → O login gerado é: driver_ref + '_d'
             → A senha inicial é o próprio driver_ref (hash bcrypt gerado pelo banco)

        Isso demonstra o conceito de Trigger: lógica de negócio no nível
        do banco de dados, executada transparentemente a cada DML.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO drivers (driver_ref, given_name, family_name, date_of_birth, country_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (ref, given_name, family_name, dob, country_id)
            )
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Erro ao cadastrar piloto: {e}")
            raise e
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_r1_status_report(self):
        """
        Relatório R1: Distribuição de resultados por status de corrida.

        Conceito de BD: Consulta em View (Virtual Table).
        --------------------------------------------------
        Em vez de executar a query complexa de JOIN + GROUP BY diretamente,
        consultamos a VIEW 'vw_relatorio_status', que encapsula essa lógica.

        Vantagens das Views:
          - Simplificam consultas complexas (o código Python fica limpo)
          - Garantem que a mesma lógica seja usada em todo o sistema
          - Permitem controle de acesso mais granular no nível do banco
          - A view é executada como uma subquery internamente pelo PostgreSQL

        A view vw_relatorio_status é definida como:
          SELECT st.status AS status_nome, COUNT(r.id) AS contagem
          FROM results r JOIN status st ON r.status_id = st.id
          GROUP BY st.status ORDER BY contagem DESC
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            # Consulta à view — o banco executa internamente o JOIN + GROUP BY
            cursor.execute("SELECT status_nome, contagem FROM vw_relatorio_status")
            res = cursor.fetchall()
            cursor.close()
            return [{'status': row[0], 'contagem': row[1]} for row in res]
        except Exception as e:
            print(f"Erro no relatório R1: {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_r2_airports_report(self, city_name):
        """
        Relatório R2: Aeroportos próximos a uma cidade-sede de corrida.

        Conceito de BD: Stored Function parametrizada com cálculo geoespacial.
        -----------------------------------------------------------------------
        A função 'get_relatorio_aeroportos_proximos(p_cidade)' é uma
        Stored Function (função armazenada) definida em PL/pgSQL no banco.

        Ela implementa:
          - CROSS JOIN entre cidades e aeroportos (produto cartesiano)
          - Cálculo de distância usando a fórmula de Haversine
            (distância entre dois pontos na superfície esférica da Terra)
          - Filtro de raio <= 100km e tipo (medium_airport / large_airport)
          - Ordenação por distância crescente

        Vantagens das Stored Functions:
          - Lógica complexa fica centralizada no banco (reutilizável)
          - Reduz tráfego de rede (o banco processa e retorna só o resultado)
          - Podem ser otimizadas pelo planner do PostgreSQL

        O parâmetro %s evita SQL Injection no nome da cidade.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            # Invoca a stored function passando o nome da cidade como parâmetro
            cursor.execute(
                "SELECT * FROM get_relatorio_aeroportos_proximos(%s)",
                (city_name,)
            )
            res = cursor.fetchall()
            cursor.close()
            return [{
                'cidade_pesquisada': row[0],
                'iata_code': row[1],
                'nome_aeroporto': row[2],
                'cidade_aeroporto': row[3],
                'distancia': round(row[4], 2),
                'tipo_aeroporto': row[5]
            } for row in res]
        except Exception as e:
            print(f"Erro no relatório R2 para '{city_name}': {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_r3_hierarchy_report(self):
        """
        Relatório R3: Relatório hierárquico de Circuitos → Corridas → Escuderias.

        Conceito de BD: Múltiplas queries com Views e reconstrução hierárquica em Python.
        ----------------------------------------------------------------------------------
        Este relatório combina dados de duas views e uma query inline:
          - vw_relatorio_circuitos_voltas: agrega métricas no nível do Circuito
            (quantidade de corridas, mínimo/média/máximo de voltas)
          - vw_relatorio_corridas_detalhe: detalha cada corrida com voltas e pilotos
          - Query inline: conta pilotos distintos por escuderia via LEFT JOIN + GROUP BY

        Estrutura do processamento Python:
          1. Busca todas as corridas indexadas por circuit_id (dicionário)
          2. Busca todos os circuitos com suas métricas agregadas
          3. Combina os dois: cada circuito recebe sua lista de corridas filha
          → Isso cria uma estrutura hierárquica (árvore) em memória

        Conceito de JOIN usado nas views:
          - LEFT JOIN entre circuits e races: inclui circuitos sem corridas
          - LEFT JOIN entre races e results: inclui corridas sem resultados registrados
          - COALESCE: substitui NULL por 0 (ex: corridas sem voltas registradas)

        Conceito de GROUP BY:
          - Agrupa por circuit_id/race_id para calcular funções de agregação
            (MIN, AVG, MAX, COUNT) por grupo.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()

            # Passo 0: Obter escuderias e quantidade de pilotos distintos
            # COUNT(DISTINCT r.driver_id): conta pilotos únicos (evita duplicatas
            # causadas por múltiplas corridas do mesmo piloto pela escuderia)
            # LEFT JOIN: inclui escuderias que nunca tiveram resultados
            cursor.execute(
                """
                SELECT c.name, COUNT(DISTINCT r.driver_id) AS qtd_pilotos
                FROM constructors c
                LEFT JOIN results r ON c.id = r.constructor_id
                GROUP BY c.id, c.name
                ORDER BY qtd_pilotos DESC, c.name ASC
                """
            )
            escuderias_rows = cursor.fetchall()
            escuderias = [{'nome': r[0], 'qtd_pilotos': r[1]} for r in escuderias_rows]

            # Passo 1: Total geral de corridas (para o cabeçalho do relatório)
            cursor.execute("SELECT COUNT(*) FROM races")
            total_corridas = cursor.fetchone()[0]

            # Passo 2: Circuitos com métricas agregadas (Nível 2 da hierarquia)
            # A view encapsula: LEFT JOIN races + subquery de max_laps por corrida
            cursor.execute(
                """
                SELECT circuit_id, circuit_name, qtd_corridas, min_voltas, avg_voltas, max_voltas 
                FROM vw_relatorio_circuitos_voltas
                ORDER BY circuit_name ASC
                """
            )
            circuitos_rows = cursor.fetchall()

            # Passo 3: Detalhes de todas as corridas (Nível 3 da hierarquia)
            # A view encapsula: JOIN seasons + LEFT JOIN results + GROUP BY
            cursor.execute(
                """
                SELECT circuit_id, race_name, race_year, voltas, qtd_pilotos 
                FROM vw_relatorio_corridas_detalhe
                ORDER BY race_year DESC, race_name ASC
                """
            )
            corridas_rows = cursor.fetchall()
            cursor.close()

            # Agrupa corridas por circuit_id em um dicionário para acesso O(1)
            # Isso evita um loop aninhado (O(n²)) ao montar a hierarquia
            corridas_por_circuito = {}
            for row in corridas_rows:
                c_id = row[0]
                corrida = {
                    'nome': row[1],
                    'ano': row[2],
                    'voltas': row[3],
                    'pilotos': row[4]
                }
                if c_id not in corridas_por_circuito:
                    corridas_por_circuito[c_id] = []
                corridas_por_circuito[c_id].append(corrida)

            # Monta a estrutura final: cada circuito recebe sua lista de corridas
            circuitos = []
            for row in circuitos_rows:
                c_id = row[0]
                circuitos.append({
                    'id': c_id,
                    'nome': row[1],
                    'qtd_corridas': row[2],
                    'min_voltas': row[3],
                    'avg_voltas': float(row[4]) if row[4] is not None else 0,
                    'max_voltas': row[5],
                    # dict.get() retorna [] se o circuito não tiver corridas registradas
                    'corridas': corridas_por_circuito.get(c_id, [])
                })

            return {
                'escuderias': escuderias,
                'total_corridas': total_corridas,
                'circuitos': circuitos
            }
        except Exception as e:
            print(f"Erro no relatório R3: {e}")
            return {'escuderias': [], 'total_corridas': 0, 'circuitos': []}
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_dashboard_corridas_recentes(self):
        """
        Busca detalhes das corridas da última temporada registrada.

        Conceito de BD: Stored Function sem parâmetros.
        ------------------------------------------------
        A função 'get_dashboard_corridas_temporada_recente()' encapsula
        internamente a lógica de:
          1. Identificar a temporada mais recente (SELECT id FROM seasons
             ORDER BY year DESC LIMIT 1)
          2. Buscar todas as corridas dessa temporada com JOIN em circuits
          3. Calcular o máximo de voltas via LEFT JOIN em results

        Isso demonstra como Stored Functions podem encapsular lógica
        multi-step que envolveria múltiplas queries no código da aplicação.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            # Invoca a função sem parâmetros — ela resolve internamente qual é a temporada mais recente
            cursor.execute("SELECT * FROM get_dashboard_corridas_temporada_recente()")
            res = cursor.fetchall()
            cursor.close()
            return [{
                'nome': row[0],
                'circuito': row[1],
                # strftime formata o objeto date Python em string legível para o template
                'data': row[2].strftime('%d/%m/%Y') if row[2] else 'N/A',
                'hora': str(row[3])[:5] if row[3] else 'N/A',
                'voltas': row[4] or 0,
                'round': row[5]
            } for row in res]
        except Exception as e:
            print(f"Erro ao buscar corridas recentes: {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_dashboard_escuderias_recentes(self):
        """
        Agrega vitórias e pontos das escuderias na última temporada.

        Conceito de BD: Stored Function com agregação e filtro por temporada.
        -----------------------------------------------------------------------
        A função encapsula: SUM(points), SUM(CASE WHEN position='1') e
        JOIN com races filtrado por season_id (última temporada).
        COALESCE(SUM(...), 0) evita NULL quando a escuderia não tem pontos.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM get_dashboard_escuderias_temporada_recente()")
            res = cursor.fetchall()
            cursor.close()
            return [{
                'nome': row[0],
                'pontos': float(row[1]) if row[1] is not None else 0,
                'vitorias': row[2] or 0
            } for row in res]
        except Exception as e:
            print(f"Erro ao buscar escuderias recentes: {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_dashboard_pilotos_recentes(self):
        """
        Agrega vitórias e pontos dos pilotos na última temporada.

        Conceito de BD: Stored Function com múltiplos JOINs e agregação.
        -----------------------------------------------------------------
        A função encapsula JOIN entre drivers, results, constructors e races,
        filtrado pela última season. GROUP BY agrupa por piloto e escuderia
        para calcular pontos e vitórias acumuladas na temporada.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM get_dashboard_pilotos_temporada_recente()")
            res = cursor.fetchall()
            cursor.close()
            return [{
                'nome': row[0],
                'escuderia': row[1],
                'pontos': float(row[2]) if row[2] is not None else 0,
                'vitorias': row[3] or 0
            } for row in res]
        except Exception as e:
            print(f"Erro ao buscar pilotos recentes: {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)
