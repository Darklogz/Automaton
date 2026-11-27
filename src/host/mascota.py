from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QGuiApplication, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QLineEdit, QMenu, QVBoxLayout, QWidget

from login import MAX_INTENTOS, credenciales_validas

# ------------------------------------------------------------ configuración
ASSETS = Path(__file__).resolve().parents[2] / "assets"

ANCHO_MASCOTA = 400   # ancho en pantalla (px); las imágenes se escalan a esto
MARGEN = 12           # separación respecto a la esquina inferior izquierda
FUENTE = "Segoe UI"
TAMANO_FUENTE = 11    # tamaño máximo; baja solo si el texto no cabe en el globo
MAX_CARACTERES = 140  # el globo muestra un resumen corto

# Zona de texto de cada globo en píxeles de la IMAGEN ORIGINAL: (x, y, ancho, alto).
# Estos valores salen de medir tus mockups tal cual (499x418, sin recortar).
# Cuando tengas el arte final, mídelos de nuevo y cámbialos aquí.
GLOBO_DIALOGO = (89, 237, 134, 55)
GLOBO_NUBE = (88, 228, 74, 62)

ESTADOS = {
    "reposo": {"archivo": "reposo.png", "texto": None},
    "login": {"archivo": "login.png", "texto": GLOBO_DIALOGO},
    "pensando": {"archivo": "pensando.png", "texto": GLOBO_NUBE},
    "respondiendo": {"archivo": "respondiendo.png", "texto": GLOBO_DIALOGO},
    "no_entendi": {"archivo": "no_entendi.png", "texto": GLOBO_DIALOGO},
}
# -------------------------------------------------------------------------


class Mascota(QWidget):
    login_exitoso = Signal()
    login_fallido = Signal()

    _FLAGS = Qt.AlignmentFlag.AlignCenter.value | Qt.TextFlag.TextWordWrap.value

    def __init__(self):
        super().__init__()
        self._pixmaps = {}
        self._escalas = {}
        self._estado = "reposo"
        self._texto = ""
        self._texto_ajuste = ""
        self._puntos = 0
        self._intentos = 0

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self._cargar_imagenes()
        self._crear_login()

        self._timer_puntos = QTimer(self)
        self._timer_puntos.timeout.connect(self._animar_puntos)
        self._timer_reposo = QTimer(self)
        self._timer_reposo.setSingleShot(True)
        self._timer_reposo.timeout.connect(self.reposo)

        self._colocar_en_esquina()

    # ------------------------------------------------------------ carga
    def _cargar_imagenes(self):
        faltan = []
        for estado, datos in ESTADOS.items():
            ruta = ASSETS / datos["archivo"]
            pm = QPixmap(str(ruta))
            if pm.isNull():
                faltan.append(str(ruta))
                continue
            self._escalas[estado] = ANCHO_MASCOTA / pm.width()
            self._pixmaps[estado] = pm.scaledToWidth(
                ANCHO_MASCOTA, Qt.TransformationMode.SmoothTransformation
            )
        if faltan:
            raise FileNotFoundError(
                "Faltan imágenes de la mascota:\n  " + "\n  ".join(faltan)
            )
        ancho = max(p.width() for p in self._pixmaps.values())
        alto = max(p.height() for p in self._pixmaps.values())
        self.setFixedSize(ancho, alto)

    def _crear_login(self):
        self._caja_login = QWidget(self)
        estilo = (
            "QLineEdit { background: white; color: #222; border: 1px solid #333;"
            " border-radius: 6px; padding: 1px 6px; font-size: 11px; }"
        )
        self._in_usuario = QLineEdit()
        self._in_usuario.setPlaceholderText("Usuario")
        self._in_password = QLineEdit()
        self._in_password.setPlaceholderText("Contraseña")
        self._in_password.setEchoMode(QLineEdit.EchoMode.Password)
        for campo in (self._in_usuario, self._in_password):
            campo.setStyleSheet(estilo)

        layout = QVBoxLayout(self._caja_login)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(3)
        layout.addWidget(self._in_usuario)
        layout.addWidget(self._in_password)

        self._in_usuario.returnPressed.connect(lambda: self._in_password.setFocus())
        self._in_password.returnPressed.connect(self._validar_login)
        self._caja_login.hide()

    # ------------------------------------------------------------ API pública
    def reposo(self):
        self._set_estado("reposo")

    def pedir_login(self):
        self._intentos = 0
        self._in_password.setPlaceholderText("Contraseña")
        self._set_estado("login")
        self.activateWindow()
        self._in_usuario.setFocus()

    def pensar(self):
        self._puntos = 0
        self._set_estado("pensando", "Pensando", ajuste="Pensando...")
        self._timer_puntos.start(400)

    def decir(self, texto, segundos=8):
        self._mostrar_temporal("respondiendo", texto, segundos)

    def no_entendi(self, texto="No te entendí", segundos=4):
        self._mostrar_temporal("no_entendi", texto, segundos)

    def modo_pasivo(self):
        """Tras el login: la mascota ya no le quita el foco a la ventana activa."""
        self.setWindowFlag(Qt.WindowType.WindowDoesNotAcceptFocus, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.show()
        self._colocar_en_esquina()

    # ------------------------------------------------------------ internos
    def _mostrar_temporal(self, estado, texto, segundos):
        if len(texto) > MAX_CARACTERES:
            texto = texto[: MAX_CARACTERES - 1].rstrip() + "…"
        self._set_estado(estado, texto)
        self._timer_reposo.start(int(segundos * 1000))

    def _set_estado(self, estado, texto="", ajuste=None):
        self._timer_puntos.stop()
        self._timer_reposo.stop()
        self._estado = estado
        self._texto = texto
        self._texto_ajuste = ajuste or texto
        es_login = estado == "login"
        self._caja_login.setVisible(es_login)
        if es_login:
            self._caja_login.setGeometry(self._rect_texto("login").toRect())
        self.update()

    def _animar_puntos(self):
        self._puntos = (self._puntos + 1) % 4
        self._texto = "Pensando" + "." * self._puntos
        self.update()

    def _validar_login(self):
        if credenciales_validas(self._in_usuario.text(), self._in_password.text()):
            self._in_usuario.clear()
            self._in_password.clear()
            self.login_exitoso.emit()
            return

        self._intentos += 1
        restantes = MAX_INTENTOS - self._intentos
        if restantes <= 0:
            self.login_fallido.emit()
            return
        self._in_password.clear()
        self._in_password.setPlaceholderText(f"Incorrecto, quedan {restantes}")
        self._in_password.setFocus()

    def _rect_texto(self, estado):
        area = ESTADOS[estado]["texto"]
        if area is None:
            return None
        x, y, w, h = area
        e = self._escalas[estado]
        oy = self.height() - self._pixmaps[estado].height()
        return QRectF(x * e, oy + y * e, w * e, h * e)

    def _colocar_en_esquina(self):
        zona = QGuiApplication.primaryScreen().availableGeometry()
        self.move(
            zona.left() + MARGEN,
            zona.top() + zona.height() - self.height() - MARGEN,
        )

    def _fuente_ajustada(self, p, rect, texto):
        fuente = QFont(FUENTE, TAMANO_FUENTE)
        for tam in range(TAMANO_FUENTE, 5, -1):
            fuente = QFont(FUENTE, tam)
            p.setFont(fuente)
            caja = p.boundingRect(rect, self._FLAGS, texto)
            if caja.height() <= rect.height() and caja.width() <= rect.width():
                break
        return fuente

    # ------------------------------------------------------------ eventos
    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        pm = self._pixmaps[self._estado]
        p.drawPixmap(0, self.height() - pm.height(), pm)

        if self._estado == "login" or not self._texto:
            return
        rect = self._rect_texto(self._estado)
        if rect is None:
            return
        p.setPen(QColor("#222222"))
        p.setFont(self._fuente_ajustada(p, rect, self._texto_ajuste))
        p.drawText(rect, self._FLAGS, self._texto)

    def contextMenuEvent(self, evento):
        menu = QMenu(self)
        menu.addAction("Salir", QApplication.quit)
        menu.exec(evento.globalPos())