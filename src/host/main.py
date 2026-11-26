import sys

import httpx
from PySide6.QtWidgets import QApplication, QMessageBox

from login import pedir_login

NUCLEO_URL = "http://localhost:8000"


def nucleo_disponible() -> bool:
    try:
        r = httpx.get(f"{NUCLEO_URL}/health", timeout=3)
        return r.status_code == 200
    except httpx.HTTPError:
        return False


def main() -> int:
    app = QApplication(sys.argv)

    if not pedir_login():
        return 0

    if nucleo_disponible():
        QMessageBox.information(
            None, "Asistente IA", "Sesión iniciada. Núcleo IA conectado."
        )
    else:
        QMessageBox.warning(
            None,
            "Asistente IA",
            "Sesión iniciada, pero el Núcleo IA no responde.\n"
            "Ejecuta: docker compose up -d",
        )

    # TODO: aquí se iniciarán la mascota y el ciclo del asistente
    return 0


if __name__ == "__main__":
    sys.exit(main())