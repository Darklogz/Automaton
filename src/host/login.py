import hashlib
import hmac

USUARIO = "usuario"
# SHA-256 de la contraseña ("123")
PASSWORD_SHA256 = "a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3"
MAX_INTENTOS = 3


def _hash(texto: str) -> str:
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def credenciales_validas(usuario: str, password: str) -> bool:
    usuario_ok = hmac.compare_digest(
        usuario.strip().encode("utf-8"), USUARIO.encode("utf-8")
    )
    password_ok = hmac.compare_digest(
        _hash(password).encode("utf-8"), PASSWORD_SHA256.encode("utf-8")
    )
    return usuario_ok and password_ok