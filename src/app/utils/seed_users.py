import os
import sys
import bcrypt

# Adiciona o diretório raiz ao python path para conseguir importar config
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from src.config.database import get_connection, return_connection

def seed_users():
    print("Iniciando seed de usuários...")
    conn = get_connection()
    cursor = conn.cursor()
    
    try:
        # Verificação rápida: se já existem usuários, não precisa re-sedar
        cursor.execute("SELECT COUNT(*) FROM USERS")
        total = cursor.fetchone()[0]
        if total > 100:
            print(f"Seed ignorado: USERS já possui {total} registros.")
            cursor.close()
            return_connection(conn)
            return
        
        # Usa rounds=10 para ser mais rápido (ainda seguro)
        salt = bcrypt.gensalt(rounds=10)
        
        # 1. Inserir Admin se não existir
        admin_login = "admin"
        admin_pass = "admin"
        hashed_admin_pass = bcrypt.hashpw(admin_pass.encode('utf-8'), salt).decode('utf-8')
        
        cursor.execute(
            "INSERT INTO USERS (login, password, tipo) VALUES (%s, %s, 'Admin') ON CONFLICT (login) DO NOTHING",
            (admin_login, hashed_admin_pass)
        )
        print("Usuário Admin processado.")
        
        # 2. Obter todos os pilotos
        cursor.execute("SELECT id, driver_ref FROM drivers")
        drivers = cursor.fetchall()
        print(f"Encontrados {len(drivers)} pilotos. Processando senhas e inserindo em USERS...")
        
        for driver_id, driver_ref in drivers:
            login = f"{driver_ref}_d"
            hashed_pass = bcrypt.hashpw(driver_ref.encode('utf-8'), salt).decode('utf-8')
            cursor.execute(
                """
                INSERT INTO USERS (login, password, tipo, id_original)
                VALUES (%s, %s, 'Piloto', %s)
                ON CONFLICT (login) DO NOTHING
                """,
                (login, hashed_pass, driver_id)
            )
            
        print("Todos os pilotos cadastrados em USERS.")
        
        # 3. Obter todas as escuderias
        cursor.execute("SELECT id, constructor_ref FROM constructors")
        constructors = cursor.fetchall()
        print(f"Encontrados {len(constructors)} construtores. Processando senhas e inserindo em USERS...")
        
        for const_id, const_ref in constructors:
            login = f"{const_ref}_c"
            hashed_pass = bcrypt.hashpw(const_ref.encode('utf-8'), salt).decode('utf-8')
            cursor.execute(
                """
                INSERT INTO USERS (login, password, tipo, id_original)
                VALUES (%s, %s, 'Escuderia', %s)
                ON CONFLICT (login) DO NOTHING
                """,
                (login, hashed_pass, const_id)
            )
            
        print("Todas as escuderias cadastradas em USERS.")
        
        conn.commit()
        print("Seed concluído com SUCESSO!")
        
    except Exception as e:
        conn.rollback()
        print(f"Erro ao executar seed: {e}")
        raise e
    finally:
        cursor.close()
        return_connection(conn)

if __name__ == "__main__":
    seed_users()

