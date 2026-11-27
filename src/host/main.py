import logging
import sys

import httpx
from PySide6.QtCore import QObject, QThread, QTimer, Signal, Slot
from PySide6.QtWidgets import QApplication, QMessageBox

from mascota import Mascota
from rutas import LOGS

NUCLEO_URL = "http://localhost:8000"

# Códigos de error que muestra la mascota
E_NUCLEO = "E001"        # El Núcleo IA no responde
E_NUCLEO_HTTP = "E002"   # El Núcleo IA responde con un error HTTP
E_INESPERADO = "E999"    # Excepción no controlada


class ComprobadorNucleo(QThread):
    resultado = Signal(int)  # código HTTP; 0 = sin conexión

    def run(self):
        try:
            r = httpx.get(f"{NUCLEO_URL}/health", timeout=3)
            self.resultado.emit(r.status_code)
        except httpx.HTTPError as error:
            logging.warning("Núcleo sin conexión: %s", error)
            self.resultado.emit(0)
        except Exception:
            logging.exception("Fallo inesperado al comprobar el Núcleo")
            self.resultado.emit(0)


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

    def mostrar_error(self, codigo, mensaje=""):
        logging.error("Error %s: %s", codigo, mensaje)
        self.mascota.error(codigo, mensaje)

    @Slot()
    def al_entrar(self):
        self.mascota.modo_pasivo()
        self.mascota.pensar()
        self.hilo = ComprobadorNucleo()
        self.hilo.resultado.connect(self.al_comprobar_nucleo)
        self.hilo.start()

    @Slot(int)
    def al_comprobar_nucleo(self, http):
        if http == 200:
            self.mascota.decir("¡Listo! Núcleo IA conectado.")
        elif http == 0:
            self.mostrar_error(
                E_NUCLEO, "El Núcleo IA no responde. ¿Docker está encendido?"
            )
        else:
            self.mostrar_error(E_NUCLEO_HTTP, f"El Núcleo IA devolvió HTTP {http}.")

    @Slot()
    def al_fallar(self):
        self.mascota.decir("Demasiados intentos. Cerrando…", 3)
        QTimer.singleShot(2500, QApplication.quit)


def instalar_manejo_de_errores(aplicacion):
    """Cualquier excepción no controlada se loguea y se muestra en la mascota."""

    def manejar(tipo, valor, traza):
        if issubclass(tipo, KeyboardInterrupt):
            sys.__excepthook__(tipo, valor, traza)
            return
        logging.error("Excepción no controlada", exc_info=(tipo, valor, traza))
        sys.__excepthook__(tipo, valor, traza)
        try:
            aplicacion.mostrar_error(E_INESPERADO, f"{tipo.__name__}: {valor}")
        except Exception:
            pass

    sys.excepthook = manejar


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    LOGS.mkdir(exist_ok=True)
    logging.basicConfig(
        filename=LOGS / "asistente.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        encoding="utf-8",
    )

    try:
        aplicacion = Aplicacion()
    except (FileNotFoundError, ValueError) as error:
        logging.error("No se pudo crear la mascota: %s", error)
        QMessageBox.critical(None, "Asistente IA", str(error))
        return 1

    instalar_manejo_de_errores(aplicacion)
    aplicacion.iniciar()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())