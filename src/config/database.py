"""
Módulo de configuração e gerenciamento de conexões com o PostgreSQL.

Conceito de BD aplicado: Pool de Conexões (Connection Pool)
-----------------------------------------------------------
Em vez de abrir e fechar uma conexão com o banco a cada requisição HTTP
(operação custosa), o Pool de Conexões mantém um conjunto fixo de conexões
abertas e as reutiliza. Isso melhora drasticamente o desempenho da aplicação.

O psycopg2.pool.SimpleConnectionPool funciona assim:
  - minconn (1): número mínimo de conexões mantidas abertas permanentemente.
  - maxconn (20): número máximo de conexões simultâneas permitidas.
  - getconn(): "empresta" uma conexão do pool para uso.
  - putconn(): "devolve" a conexão ao pool após o uso.
"""

import psycopg2
from psycopg2 import pool
import os
import time

# -----------------------------------------------------------------------
# Configuração de conexão com PostgreSQL via variáveis de ambiente.
# Usar variáveis de ambiente é uma boa prática de segurança: evita
# credenciais hardcoded no código-fonte (especialmente em repositórios).
# Os valores padrão ('db', 5432, etc.) são usados quando as variáveis
# não estão definidas — conveniente no ambiente Docker local.
# -----------------------------------------------------------------------
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'db'),       # 'db' é o nome do serviço no docker-compose
    'port': int(os.getenv('DB_PORT', '5432')), # Porta padrão do PostgreSQL
    'user': os.getenv('DB_USER', 'arvore_user'),
    'password': os.getenv('DB_PASSWORD', 'arvore_pass'),
    'database': os.getenv('DB_NAME', 'arvore_urbana')
}

# -----------------------------------------------------------------------
# Inicialização do Pool de Conexões com mecanismo de retry.
# O retry é necessário porque, ao usar Docker Compose, o container da
# aplicação Python pode iniciar antes do container do PostgreSQL estar
# completamente pronto para aceitar conexões.
# -----------------------------------------------------------------------
connection_pool = None
max_retries = 30    # Número máximo de tentativas
retry_delay = 2     # Segundos de espera entre tentativas

for attempt in range(max_retries):
    try:
        # Cria o pool com entre 1 e 20 conexões simultâneas.
        # O pool gerencia quais conexões estão "em uso" e quais estão "livres".
        connection_pool = psycopg2.pool.SimpleConnectionPool(
            1, 20,
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database']
        )

        if connection_pool:
            print('Conexão com PostgreSQL realizada com SUCESSO!')
            break
        else:
            print('Erro ao criar pool de conexões')
    except (Exception, psycopg2.Error) as error:
        if attempt < max_retries - 1:
            print(f'Tentativa {attempt + 1}/{max_retries}: Aguardando PostgreSQL... ({error})')
            time.sleep(retry_delay)
        else:
            print(f'Erro na conexão com PostgreSQL após {max_retries} tentativas: {error}')
            raise

def get_connection():
    """Retorna uma conexão do pool (para uso direto, fora dos DAOs)."""
    return connection_pool.getconn()

def return_connection(connection):
    """Devolve uma conexão ao pool após o uso."""
    connection_pool.putconn(connection)
