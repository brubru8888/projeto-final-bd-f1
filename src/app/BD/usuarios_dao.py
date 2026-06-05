from src.app.utils.security import SecurityManager
from src.config.app import aplicacao

class Usuarios_dao:
    def __init__(self, db_pool):
        self._db_pool = db_pool
        # Inicializa o gerenciador de segurança
        self.security = SecurityManager(aplicacao.config['SECRET_KEY'])

    def select_na_tabela_usuarios(self, login, senha):
        """
        Valida credenciais do usuário na tabela USERS da F1
        
        Args:
            login: Login do usuário (ex: admin, hamilton_d, ferrari_c)
            senha: Senha em texto plano
            
        Returns:
            Dicionário com dados do usuário se válido, None caso contrário
        """
        sql_cons_usuarios = """
            SELECT userid, login, password, tipo, id_original
            FROM USERS
            WHERE login = %s
        """
        values = (login,)

        print("SELECT USUARIO =", sql_cons_usuarios, values)

        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute(sql_cons_usuarios, values)
            resultado = cursor.fetchone()
            cursor.close()

            if resultado:
                # Converte resultado para dicionário
                colunas = ['userid', 'login', 'password', 'tipo', 'id_original']
                usuario = dict(zip(colunas, resultado))
                
                # Verifica se a senha corresponde ao hash
                senha_hash = usuario['password']
                if self.security.verify_password(senha, senha_hash):
                    # Remove a senha do retorno por segurança
                    usuario.pop('password', None)
                    return usuario
                else:
                    raise Exception("SENHA INCORRETA")
            else:
                raise Exception("USUÁRIO NÃO EXISTE NO BD")
        except Exception as erro:
            print(f"Erro ao consultar usuários: {erro}")
            raise erro
        finally:
            if conn:
                self._db_pool.putconn(conn)

    def registrar_log_auditoria(self, userid, acao):
        """
        Registra uma ação de LOGIN ou LOGOUT na tabela USERS_LOG
        
        Args:
            userid: ID do usuário no banco
            acao: 'LOGIN' ou 'LOGOUT'
        """
        sql_log = """
            INSERT INTO USERS_LOG (userid, action)
            VALUES (%s, %s)
        """
        values = (userid, acao)
        
        conn = None
        try:
            conn = self._db_pool.getconn()
            cursor = conn.cursor()
            cursor.execute(sql_log, values)
            conn.commit()
            cursor.close()
            print(f"Log de auditoria registrado: {acao} para usuário {userid}")
            return True
        except Exception as erro:
            if conn:
                conn.rollback()
            print(f"Erro ao registrar log de auditoria: {erro}")
            return False
        finally:
            if conn:
                self._db_pool.putconn(conn)
