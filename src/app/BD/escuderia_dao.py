"""
Módulo de Acesso a Dados (DAO) para operações da Escuderia.

Conceitos de BD aplicados neste módulo:
  - Invocação de Stored Functions parametrizadas (SELECT * FROM funcao(%s))
  - Consultas com DISTINCT e filtros por FK (JOIN + WHERE)
  - Transação independente com verificação de duplicidade antes do INSERT
  - LIKE com parâmetro para busca textual case-insensitive
  - Rollback em caso de erro (Atomicidade de Transações)
"""


class Escuderia_dao:
    """
    DAO para operações relacionadas ao perfil de Escuderia.
    Todas as operações recebem o pool de conexões via construtor.
    """

    def __init__(self, db_pool):
        # O pool é injetado no construtor (Dependency Injection)
        self._db_pool = db_pool

    def get_dashboard(self, constructor_id):
        """
        Retorna KPIs de resumo da escuderia: vitórias, pilotos e período de atuação.

        Conceito de BD: Stored Function com subconsultas correlacionadas.
        -----------------------------------------------------------------
        A função 'get_escuderia_dashboard(p_constructor_id)' usa 4 subconsultas
        escalares (retornam um único valor cada) para calcular:
          - COUNT(*) WHERE position = '1': quantidade de vitórias
          - COUNT(DISTINCT driver_id): pilotos únicos que correram pela escuderia
          - MIN(year): primeiro ano de participação
          - MAX(year): último ano de participação

        Subconsultas correlacionadas são executadas para cada linha do resultado
        externo — mas como a função retorna apenas 1 linha, o custo é fixo.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            # Invoca a stored function passando o ID da escuderia logada
            cursor.execute("SELECT * FROM get_escuderia_dashboard(%s)", (constructor_id,))
            row = cursor.fetchone()
            cursor.close()
            if row:
                return {
                    'vitorias': row[0] or 0,
                    'qtd_pilotos': row[1] or 0,
                    'primeiro_ano': row[2] or 'N/A',
                    'ultimo_ano': row[3] or 'N/A'
                }
            return {'vitorias': 0, 'qtd_pilotos': 0, 'primeiro_ano': 'N/A', 'ultimo_ano': 'N/A'}
        except Exception as e:
            print(f"Erro no dashboard da escuderia {constructor_id}: {e}")
            return {'vitorias': 0, 'qtd_pilotos': 0, 'primeiro_ano': 'N/A', 'ultimo_ano': 'N/A'}
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_escuderia_info(self, constructor_id):
        """
        Recupera o nome da escuderia para exibição no cabeçalho das páginas.

        Conceito de BD: SELECT com filtro pela PK (Primary Key).
        ---------------------------------------------------------
        Filtrar por 'id' (PK) é a forma mais eficiente de buscar um registro:
        o PostgreSQL usa o índice B-Tree da PK para acesso O(log n) direto,
        evitando um Full Table Scan.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            # WHERE id = %s: acesso direto pelo índice da PK — operação O(log n)
            cursor.execute("SELECT name FROM constructors WHERE id = %s", (constructor_id,))
            row = cursor.fetchone()
            cursor.close()
            return {'nome': row[0]} if row else {'nome': 'Desconhecida'}
        except Exception as e:
            print(f"Erro ao buscar info da escuderia {constructor_id}: {e}")
            return {'nome': 'Erro'}
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_r4_vitorias_pilotos(self, constructor_id):
        """
        Relatório R4: Pilotos da escuderia ordenados por quantidade de vitórias.

        Conceito de BD: Stored Function com GROUP BY e filtro duplo.
        -------------------------------------------------------------
        A função 'get_relatorio_vitorias_pilotos(p_constructor_id)' implementa:
          - JOIN entre results e drivers para obter nome completo
          - WHERE constructor_id = p_constructor_id: filtra pela escuderia
          - WHERE position = '1': considera apenas vitórias (P1)
          - GROUP BY driver_id: agrupa por piloto para COUNT
          - ORDER BY vitorias DESC: ranking decrescente de vitórias

        Uso de Stored Function: centraliza essa lógica no banco para que
        diferentes interfaces (web, mobile, relatório) usem a mesma query.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM get_relatorio_vitorias_pilotos(%s)", (constructor_id,))
            res = cursor.fetchall()
            cursor.close()
            return [{'nome_completo': row[0], 'vitorias': row[1]} for row in res]
        except Exception as e:
            print(f"Erro no R4 da escuderia {constructor_id}: {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_r5_status_escuderia(self, constructor_id):
        """
        Relatório R5: Histórico de status (abandono, acidente, etc.) da escuderia.

        Conceito de BD: Stored Function com JOIN em tabela de domínio.
        ---------------------------------------------------------------
        A função 'get_relatorio_status_escuderia(p_constructor_id)' faz
        JOIN entre results e status (tabela de domínio que mapeia IDs para
        descrições textuais), filtra pela escuderia e agrupa por status
        para contar ocorrências.

        Tabelas de domínio (lookup tables) são uma boa prática de normalização:
        evitam redundância ao armazenar apenas o ID em 'results' em vez de
        repetir a string de status em cada linha.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM get_relatorio_status_escuderia(%s)", (constructor_id,))
            res = cursor.fetchall()
            cursor.close()
            return [{'status': row[0], 'contagem': row[1]} for row in res]
        except Exception as e:
            print(f"Erro no R5 da escuderia {constructor_id}: {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def search_drivers_by_family_name(self, family_name, constructor_id):
        """
        Busca pilotos pelo sobrenome que já tenham corrido pela escuderia logada.

        Conceito de BD: Consulta com LIKE para busca textual e DISTINCT para deduplicação.
        -----------------------------------------------------------------------------------
        - LIKE '%termo%': busca registros que contenham o termo em qualquer posição.
          O uso de 'lower()' em ambos os lados torna a busca case-insensitive.
        - JOIN results: filtra apenas pilotos que correram pela escuderia logada.
          Isso é um JOIN com filtro por FK (constructor_id).
        - DISTINCT: um piloto pode ter várias entradas em 'results' (uma por corrida),
          então DISTINCT elimina as linhas duplicadas no resultado.
        - Parâmetro f"%{family_name.lower()}%" para o LIKE: o '%' é um wildcard
          SQL que casa qualquer sequência de caracteres.

        Nota de Desempenho: LIKE com wildcard no início ('%termo') não pode usar
        índice B-Tree convencional — faz full scan. Para buscas em produção de
        grande escala, seria preferível usar Full Text Search do PostgreSQL.
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            query = """
                SELECT DISTINCT d.id, d.driver_ref, d.given_name, d.family_name, d.date_of_birth, c.name
                FROM drivers d
                LEFT JOIN countries c ON d.country_id = c.id
                JOIN results res ON res.driver_id = d.id
                WHERE lower(d.family_name) LIKE %s
                  AND res.constructor_id = %s
                ORDER BY d.family_name ASC, d.given_name ASC
            """
            # Constrói o padrão LIKE com wildcards para busca parcial
            search_param = f"%{family_name.lower()}%"
            cursor.execute(query, (search_param, constructor_id))
            res = cursor.fetchall()
            cursor.close()
            return [{
                'id': row[0],
                'driver_ref': row[1],
                'given_name': row[2],
                'family_name': row[3],
                'dob': row[4].strftime('%d/%m/%Y') if row[4] else 'N/A',
                'pais': row[5] or 'N/A'
            } for row in res]
        except Exception as e:
            print(f"Erro ao buscar pilotos por sobrenome '{family_name}': {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def insert_driver_independent_transaction(self, ref, given_name, family_name, dob, country_id):
        """
        Insere um piloto em uma transação INDEPENDENTE e isolada.

        Conceito de BD: Transações Independentes para Carga em Lote (Bulk Insert).
        --------------------------------------------------------------------------
        Esta função é usada durante o upload de pilotos via CSV.
        O princípio é: cada linha do CSV é processada em sua própria transação.
        Se uma linha falhar (ex: piloto duplicado), somente ela é revertida
        (ROLLBACK), e o processamento continua com a próxima linha.

        Isso contrasta com uma transação global: se uma linha falhasse,
        TODOS os inserts seriam revertidos — comportamento indesejado no upload.

        Propriedade ACID aplicada: Isolamento (Isolation)
          - Cada piloto é inserido ou revertido independentemente dos outros.

        A verificação de duplicidade ANTES do INSERT (SELECT + fetchone)
        é uma validação de negócio em nível de aplicação — existe também
        a constraint UNIQUE implícita no trigger do banco como segunda camada.

        Retorno: tupla (sucesso: bool, mensagem: str)
        """
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()

            # Verificação de integridade antes do INSERT:
            # Consulta se já existe um piloto com mesmo nome e sobrenome (case-insensitive)
            # Isso evita duplicatas que não seriam detectadas pela PK (que é auto-incremento)
            cursor.execute(
                "SELECT id FROM drivers WHERE lower(given_name) = lower(%s) AND lower(family_name) = lower(%s)",
                (given_name, family_name)
            )
            if cursor.fetchone():
                cursor.close()
                return False, f"Um piloto chamado '{given_name} {family_name}' já existe na base de dados."

            # INSERT do piloto — se bem-sucedido, os triggers BEFORE e AFTER serão disparados:
            # BEFORE: verifica login duplicado em USERS
            # AFTER: cria usuário do tipo 'Piloto' em USERS automaticamente
            cursor.execute(
                """
                INSERT INTO drivers (driver_ref, given_name, family_name, date_of_birth, country_id)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (ref, given_name, family_name, dob, country_id)
            )
            # COMMIT da transação individual — persiste APENAS este piloto
            conn.commit()
            cursor.close()
            return True, "Sucesso"
        except Exception as e:
            if conn:
                # ROLLBACK: garante que este piloto não seja parcialmente inserido
                conn.rollback()
            # Extrai apenas a primeira linha do erro do PostgreSQL (mais legível)
            error_msg = str(e).split('\n')[0]
            return False, error_msg
        finally:
            if conn:
                self._db_pool.putconn(conn)
