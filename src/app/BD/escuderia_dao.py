class Escuderia_dao:
    def __init__(self, db_pool):
        self._db_pool = db_pool

    def get_dashboard(self, constructor_id):
        """Retorna estatísticas do dashboard da escuderia"""
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
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
        """Retorna as informações da escuderia para a UI"""
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
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
        """R4: Lista vitórias por piloto da escuderia logada"""
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
        """R5: Lista status por quantidade da escuderia logada"""
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

    def search_drivers_by_family_name(self, family_name):
        """Busca pilotos cujo sobrenome contenha a string pesquisada"""
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            query = """
                SELECT d.id, d.driver_ref, d.given_name, d.family_name, d.date_of_birth, c.name
                FROM drivers d
                LEFT JOIN countries c ON d.country_id = c.id
                WHERE lower(d.family_name) LIKE %s
                ORDER BY d.family_name ASC, d.given_name ASC
            """
            search_param = f"%{family_name.lower()}%"
            cursor.execute(query, (search_param,))
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
        Insere um piloto em uma transação independente.
        Retorna (True, None) se sucesso, ou (False, mensagem_erro) se falha.
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
            return True, "Sucesso"
        except Exception as e:
            if conn:
                conn.rollback()
            # Captura a mensagem de erro da exceção do banco
            error_msg = str(e).split('\n')[0]
            return False, error_msg
        finally:
            if conn:
                self._db_pool.putconn(conn)
