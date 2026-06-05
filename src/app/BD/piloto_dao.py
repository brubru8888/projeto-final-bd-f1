class Piloto_dao:
    def __init__(self, db_pool):
        self._db_pool = db_pool

    def get_years(self, driver_id):
        """Retorna o primeiro e último ano em que o piloto competiu"""
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
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
            print(f"Erro ao obter anos do piloto {driver_id}: {e}")
            return {'primeiro_ano': 'N/A', 'ultimo_ano': 'N/A'}
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def get_dashboard_details(self, driver_id):
        """Retorna os detalhes de desempenho do piloto por ano e circuito"""
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM get_piloto_dashboard_details(%s)", (driver_id,))
            res = cursor.fetchall()
            cursor.close()
            return [{
                'ano': row[0],
                'circuito': row[1],
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
        """R6: Pontos obtidos por ano e corridas do piloto logado"""
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
        """R7: Status das corridas do piloto logado"""
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
