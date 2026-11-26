import hashlib
import hmac

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

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


class LoginDialog(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Asistente IA")
        self.setFixedWidth(320)
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)
        self.intentos = 0

        titulo = QLabel("Iniciar sesión")
        titulo.setAlignment(Qt.AlignCenter)
        titulo.setStyleSheet("font-size: 18px; font-weight: bold;")

        self.input_usuario = QLineEdit()
        self.input_usuario.setPlaceholderText("Usuario")

        self.input_password = QLineEdit()
        self.input_password.setPlaceholderText("Contraseña")
        self.input_password.setEchoMode(QLineEdit.Password)

        self.mensaje = QLabel("")
        self.mensaje.setAlignment(Qt.AlignCenter)
        self.mensaje.setWordWrap(True)
        self.mensaje.setStyleSheet("color: #d9534f;")

        boton = QPushButton("Entrar")
        boton.setDefault(True)
        boton.clicked.connect(self.validar)

        self.input_usuario.returnPressed.connect(
            lambda: self.input_password.setFocus()
        )
        self.input_password.returnPressed.connect(self.validar)

        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(titulo)
        layout.addWidget(self.input_usuario)
        layout.addWidget(self.input_password)
        layout.addWidget(self.mensaje)
        layout.addWidget(boton)

    def validar(self):
        if credenciales_validas(
            self.input_usuario.text(), self.input_password.text()
        ):
            self.accept()
            return

        self.intentos += 1
        restantes = MAX_INTENTOS - self.intentos
        if restantes <= 0:
            self.reject()
            return

        self.mensaje.setText(
            f"Usuario o contraseña incorrectos. Intentos restantes: {restantes}"
        )
        self.input_password.clear()
        self.input_password.setFocus()


def pedir_login() -> bool:
    """Muestra el login. Devuelve True si el usuario entró."""
    return bool(LoginDialog().exec())