"""Segurança de autenticação: hash de senha e token assinado."""
import bcrypt
import secrets
from datetime import datetime
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired


class SecurityManager:
    """Gerencia hash de senha e token assinado."""
    
    def __init__(self, secret_key):
        self.secret_key = secret_key
        self.serializer = URLSafeTimedSerializer(secret_key)
        self.token_expiration_hours = 24

    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            print(f"Erro ao verificar senha: {e}")
            return False
    
    def generate_token(self, user_email: str) -> str:
        payload = {
            'email': user_email,
            'timestamp': datetime.utcnow().isoformat()
        }
        token = self.serializer.dumps(
            payload,
            salt='auth-token'
        )
        return token
    
    def verify_token(self, token: str) -> dict:
        try:
            payload = self.serializer.loads(
                token,
                salt='auth-token',
                max_age=self.token_expiration_hours * 3600
            )
            return payload
        except SignatureExpired:
            print("Token expirado")
            return None
        except BadSignature:
            print("Token inválido")
            return None
        except Exception as e:
            print(f"Erro ao verificar token: {e}")
            return None
    
    def generate_csrf_token(self) -> str:
        return secrets.token_urlsafe(32)

