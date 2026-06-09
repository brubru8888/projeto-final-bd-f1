"""
Módulo de Acesso a Dados (DAO) para autenticação e auditoria de usuários.

Conceitos de BD aplicados neste módulo:
  - SELECT com filtro por coluna indexada (UNIQUE) para autenticação
  - Verificação de senha com hash bcrypt (segurança de dados no banco)
  - INSERT em tabela de log/auditoria (USERS_LOG)
  - Gerenciamento de transação (COMMIT / ROLLBACK)
  - Uso da tabela de sistema USERS criada especificamente para este projeto
"""

from src.app.utils.security import SecurityManager
from src.config.app import aplicacao


class Usuarios_dao:
    """
    DAO responsável por autenticação e registro de auditoria de usuários.
    
    A tabela USERS centraliza todos os tipos de usuário (Admin, Escuderia, Piloto)
    com o campo 'tipo' indicando o perfil e 'id_original' apontando para o
    registro correspondente nas tabelas drivers ou constructors.
    """

    def __init__(self, db_pool):
        self._db_pool = db_pool
        # SecurityManager encapsula verificação de hash bcrypt e geração de tokens
        self.security = SecurityManager(aplicacao.config['SECRET_KEY'])

    def select_na_tabela_usuarios(self, login, senha):
        """
        Valida as credenciais do usuário contra a tabela USERS.

        Conceito de BD: SELECT com filtro por coluna UNIQUE + verificação de hash.
        --------------------------------------------------------------------------
        A coluna 'login' tem constraint UNIQUE, o que garante:
          1. Integridade: impossível ter dois usuários com o mesmo login
          2. Performance: o PostgreSQL cria automaticamente um índice B-Tree
             na coluna UNIQUE, tornando a busca WHERE login = %s muito eficiente

        Fluxo de autenticação:
          1. Busca o usuário pelo login (campo UNIQUE → acesso por índice)
          2. Obtém o hash bcrypt da senha armazenado no banco
          3. Verifica se a senha fornecida corresponde ao hash usando bcrypt.checkpw()
             → A senha nunca é armazenada em texto plano! Apenas o hash.
             → O bcrypt verifica a senha sem precisar "decifrar" o hash.
          4. Remove o campo 'password' do dicionário retornado (boa prática de segurança)

        As senhas são armazenadas como hashes bcrypt (gerados pela extensão pgcrypto
        do PostgreSQL via função crypt()). O bcrypt é resistente a ataques de força
        bruta por ser computacionalmente custoso.
        """
        # Query parametrizada para evitar SQL Injection
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
                # Mapeia as colunas da tupla retornada para um dicionário nomeado
                colunas = ['userid', 'login', 'password', 'tipo', 'id_original']
                usuario = dict(zip(colunas, resultado))

                # Verifica se a senha fornecida corresponde ao hash bcrypt armazenado.
                # bcrypt.checkpw() recria o hash com o mesmo salt e compara —
                # nunca armazena a senha em texto plano.
                senha_hash = usuario['password']
                if self.security.verify_password(senha, senha_hash):
                    # Remove a senha do dicionário por segurança antes de retornar
                    # (a senha não deve circular na aplicação após a verificação)
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
        Registra uma ação de LOGIN ou LOGOUT na tabela USERS_LOG.

        Conceito de BD: Tabela de Auditoria (Audit Log) com INSERT.
        ------------------------------------------------------------
        A tabela USERS_LOG é uma tabela de auditoria — registra quem fez o quê
        e quando. Ela possui:
          - userid: FK referenciando USERS (quem realizou a ação)
          - action: string controlada por CHECK constraint ('LOGIN' ou 'LOGOUT')
          - action_date: TIMESTAMP com DEFAULT NOW() — o banco define
            automaticamente a data/hora da ação sem precisar do Python

        Auditoria é um requisito comum em sistemas com múltiplos perfis de
        acesso: permite rastrear todos os acessos ao sistema e detectar
        comportamentos suspeitos (ex: muitos logins em horários incomuns).

        O campo DEFAULT NOW() é um exemplo de valor default do PostgreSQL —
        o banco preenche automaticamente sem que a aplicação precise enviar.
        """
        # O campo action_date é omitido porque tem DEFAULT NOW() no banco
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
            # COMMIT: persiste o registro de auditoria permanentemente
            conn.commit()
            cursor.close()
            print(f"Log de auditoria registrado: {acao} para usuário {userid}")
            return True
        except Exception as erro:
            if conn:
                # ROLLBACK: em caso de erro, não deixa registro parcial
                conn.rollback()
            print(f"Erro ao registrar log de auditoria: {erro}")
            return False
        finally:
            if conn:
                self._db_pool.putconn(conn)
