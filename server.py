import os
from src.config.app import aplicacao

# INICIALIZAR O SERVIDOR
if __name__ == '__main__':
    # Seed automático de usuários (admin + pilotos + escuderias)
    try:
        from src.app.utils.seed_users import seed_users
        seed_users()
    except Exception as e:
        print(f"[AVISO] Seed de usuários falhou (pode já estar populado): {e}")

    debug_mode = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    print('******** SERVIDOR DA APLICACAO NO AR!! ********')
    aplicacao.run(host='0.0.0.0', port=3000, debug=debug_mode)
