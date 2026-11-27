import sys

import httpx
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication

from mascota import Mascota

NUCLEO_URL = "http://localhost:8000"


class ComprobadorNucleo(QThread):
    resultado = Signal(bool)

    def run(self):
        try:
            r = httpx.get(f"{NUCLEO_URL}/health", timeout=3)
            self.resultado.emit(r.status_code == 200)
        except httpx.HTTPError:
            self.resultado.emit(False)


class Aplicacion(QObject):
    def __init__(self):
        super().__init__()
        self.mascota = Mascota()
        self.mascota.login_exitoso.connect(self.al_entrar)
        self.mascota.login_fallido.connect(self.al_fallar)
        self.hilo = None

    def iniciar(self):
        self.mascota.show()
        self.mascota.pedir_login()

    @Slot()
    def al_entrar(self):
        self.mascota.modo_pasivo()
        self.mascota.pensar()
        self.hilo = ComprobadorNucleo()
        self.hilo.resultado.connect(self.al_comprobar_nucleo)
        self.hilo.start()

    @Slot(bool)
    def al_comprobar_nucleo(self, conectado):
        if conectado:
            self.mascota.decir("¡Listo! Núcleo IA conectado.")
        else:
            self.mascota.decir(
                "El Núcleo IA no responde. Ejecuta: docker compose up -d", 10
            )

    @Slot()
    def al_fallar(self):
        self.mascota.decir("Demasiados intentos. Cerrando…", 3)
        QTimer.singleShot(2500, QApplication.quit)


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    try:
        aplicacion = Aplicacion()
    except FileNotFoundError as error:
        print(error)
        return 1
    aplicacion.iniciar()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())