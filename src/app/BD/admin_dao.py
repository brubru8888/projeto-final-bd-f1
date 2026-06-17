"""Acesso a dados do administrador."""


class Admin_dao:
    """Consultas do perfil administrador."""

    def __init__(self, db_pool):
        self._db_pool = db_pool

    def get_dashboard_stats(self):
        """Retorna as contagens do dashboard."""
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()

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
            if conn:
                self._db_pool.putconn(conn)

    def get_countries(self):
        """Lista países para os formulários."""
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM countries ORDER BY name ASC")
            res = cursor.fetchall()
            cursor.close()
            return [{'id': row[0], 'name': row[1]} for row in res]
        except Exception as e:
            print(f"Erro ao obter países: {e}")
            return []
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def insert_constructor(self, ref, name, country_id, wiki_url):
        """Insere uma escuderia."""
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO constructors (constructor_ref, name, country_id, wikipedia_url)
                VALUES (%s, %s, %s, %s)
                """,
                (ref, name, country_id, wiki_url or None)
            )
            conn.commit()
            cursor.close()
            return True
        except Exception as e:
            if conn:
                conn.rollback()
            print(f"Erro ao cadastrar escuderia: {e}")
            raise e
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def insert_driver(self, ref, given_name, family_name, dob, country_id):
        """Insere um piloto."""
        if not ref or not ref.strip():
            raise ValueError("A referencia do piloto (driver_ref) e obrigatoria.")
        if not given_name or not given_name.strip():
            raise ValueError("O nome do piloto (given_name) e obrigatorio.")
        if not family_name or not family_name.strip():
            raise ValueError("O sobrenome do piloto (family_name) e obrigatorio.")
        if not dob or not dob.strip():
            raise ValueError("A data de nascimento do piloto (date_of_birth) e obrigatoria.")
        if not country_id or not country_id.strip():
            raise ValueError("O pais do piloto (country_id) e obrigatorio.")

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
        """Lê a view do relatório R1."""
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
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
        """Executa o relatório R2."""
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
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
        """Monta o relatório hierárquico R3."""
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()

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

            cursor.execute("SELECT COUNT(*) FROM races")
            total_corridas = cursor.fetchone()[0]

            cursor.execute(
                """
                SELECT circuit_id, circuit_name, qtd_corridas, min_voltas, avg_voltas, max_voltas 
                FROM vw_relatorio_circuitos_voltas
                ORDER BY circuit_name ASC
                """
            )
            circuitos_rows = cursor.fetchall()

            cursor.execute(
                """
                SELECT circuit_id, race_name, race_year, voltas, qtd_pilotos 
                FROM vw_relatorio_corridas_detalhe
                ORDER BY race_year DESC, race_name ASC
                """
            )
            corridas_rows = cursor.fetchall()
            cursor.close()

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
        """Lista as corridas da temporada mais recente."""
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM get_dashboard_corridas_temporada_recente()")
            res = cursor.fetchall()
            cursor.close()
            return [{
                'nome': row[0],
                'circuito': row[1],
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
        """Lista escuderias e pontos da temporada mais recente."""
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
        """Lista pilotos e pontos da temporada mais recente."""
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
