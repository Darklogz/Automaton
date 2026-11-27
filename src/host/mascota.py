from PIL import Image
from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QGuiApplication,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from login import MAX_INTENTOS, credenciales_validas
from rutas import ASSETS

# ------------------------------------------------------------ configuración
ALTO_MASCOTA = 300      # alto en pantalla del personaje (px)
MARGEN = 12             # separación respecto a la esquina inferior izquierda

# Globo de diálogo (lo dibuja el código; los PNG no lo incluyen)
COLOR_TEXTO = "#BF5FFF"         # morado
COLOR_FONDO = (0, 0, 0, 200)    # negro semitransparente: (R, G, B, alfa 0-255)
COLOR_BORDE = "#8A2BE2"         # morado oscuro
COLOR_BORDE_ERROR = "#FF3B6B"   # rojo rosado para el estado de error
FUENTE = "Segoe UI"
TAMANO_FUENTE = 11              # máximo; baja solo si el texto no cabe
MAX_CARACTERES = 140            # el globo muestra un resumen corto
RELLENO = 12                    # espacio entre el borde del globo y el texto
RADIO = 14                      # esquinas redondeadas
COLA = 14                       # largo de la colita hacia el personaje
BURBUJA_ANCHO_MAX = 260
BURBUJA_Y = 0.10                # altura del globo: 0 = arriba, 1 = abajo
LOGIN_ANCHO = 230
LOGIN_ALTO = 108

# Imagen de cada estado (carpeta assets/)
ARCHIVOS = {
    "reposo": "reposo.png",
    "login": "login.png",
    "pensando": "pensando.png",
    "respondiendo": "respondiendo.png",
    "no_entendi": "no_entendi.png",
    "error": "error.png",
}
# -------------------------------------------------------------------------


def _leer_lienzo(ruta):
    """Devuelve (tamaño del lienzo, caja del contenido no transparente)."""
    with Image.open(ruta) as im:
        rgba = im.convert("RGBA")
        alfa = rgba.getchannel("A").point(lambda a: 255 if a > 8 else 0)
        return rgba.size, alfa.getbbox()


class Mascota(QWidget):
    login_exitoso = Signal()
    login_fallido = Signal()

    _FLAGS = Qt.AlignmentFlag.AlignCenter.value | Qt.TextFlag.TextWordWrap.value

    def __init__(self):
        super().__init__()
        self._pixmaps = {}
        self._estado = "reposo"
        self._texto = ""
        self._texto_ajuste = ""
        self._puntos = 0
        self._intentos = 0
        self._x_burbuja = 0
        self._y_burbuja = 0

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
        rutas = {estado: ASSETS / nombre for estado, nombre in ARCHIVOS.items()}
        faltan = [str(r) for r in rutas.values() if not r.is_file()]
        if faltan:
            raise FileNotFoundError(
                "Faltan imágenes de la mascota:\n  " + "\n  ".join(faltan)
            )

        datos = {estado: _leer_lienzo(r) for estado, r in rutas.items()}
        tamanos = {estado: d[0] for estado, d in datos.items()}
        if len(set(tamanos.values())) > 1:
            detalle = "\n  ".join(f"{e}: {t[0]}x{t[1]}" for e, t in tamanos.items())
            raise ValueError(
                "Todas las imágenes deben tener el mismo tamaño de lienzo:\n  "
                + detalle
            )

        cajas = [d[1] for d in datos.values() if d[1] is not None]
        if not cajas:
            raise ValueError("Las imágenes de la mascota están totalmente vacías.")

        # Mismo recorte para todos los estados, así el personaje no "salta".
        izq = min(c[0] for c in cajas)
        arriba = min(c[1] for c in cajas)
        der = max(c[2] for c in cajas)
        abajo = max(c[3] for c in cajas)
        recorte = QRect(izq, arriba, der - izq, abajo - arriba)

        for estado, ruta in rutas.items():
            pm = QPixmap(str(ruta)).copy(recorte)
            self._pixmaps[estado] = pm.scaledToHeight(
                ALTO_MASCOTA, Qt.TransformationMode.SmoothTransformation
            )

        ancho = self._pixmaps["reposo"].width()
        self._x_burbuja = ancho + COLA
        self._y_burbuja = int(ALTO_MASCOTA * BURBUJA_Y)
        self.setFixedSize(self._x_burbuja + BURBUJA_ANCHO_MAX, ALTO_MASCOTA)

    def _crear_login(self):
        self._caja_login = QWidget(self)

        estilo_campo = (
            "QLineEdit { background: rgba(25, 0, 40, 230); color: %s;"
            " border: 1px solid %s; border-radius: 6px; padding: 3px 8px;"
            " font-size: 12px; placeholder-text-color: #7A4AA8; }"
        ) % (COLOR_TEXTO, COLOR_BORDE)

        titulo = QLabel("Inicia sesión")
        titulo.setStyleSheet(
            "color: %s; font-size: 12px; font-weight: bold;"
            " background: transparent;" % COLOR_TEXTO
        )

        self._in_usuario = QLineEdit()
        self._in_usuario.setPlaceholderText("Usuario")
        self._in_password = QLineEdit()
        self._in_password.setPlaceholderText("Contraseña")
        self._in_password.setEchoMode(QLineEdit.EchoMode.Password)
        for campo in (self._in_usuario, self._in_password):
            campo.setStyleSheet(estilo_campo)

        layout = QVBoxLayout(self._caja_login)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(titulo)
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

    def error(self, codigo, mensaje="", segundos=15):
        """Muestra error.png y el código de error en el globo."""
        texto = f"Error {codigo}"
        if mensaje:
            texto += f"\n{mensaje}"
        self._mostrar_temporal("error", texto, segundos)

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
            area = self._rect_login().adjusted(RELLENO, RELLENO, -RELLENO, -RELLENO)
            self._caja_login.setGeometry(area.toRect())
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

    def _colocar_en_esquina(self):
        zona = QGuiApplication.primaryScreen().availableGeometry()
        self.move(
            zona.left() + MARGEN,
            zona.top() + zona.height() - self.height() - MARGEN,
        )

    # ------------------------------------------------------------ globo
    def _rect_login(self):
        return QRectF(self._x_burbuja, self._y_burbuja, LOGIN_ANCHO, LOGIN_ALTO)

    def _medir_texto(self, texto):
        ancho_max = BURBUJA_ANCHO_MAX - 2 * RELLENO
        alto_max = int(ALTO_MASCOTA * 0.55) - 2 * RELLENO
        area = QRect(0, 0, ancho_max, 10000)
        fuente = QFont(FUENTE, TAMANO_FUENTE)
        caja = QFontMetrics(fuente).boundingRect(area, self._FLAGS, texto)
        for tam in range(TAMANO_FUENTE, 6, -1):
            fuente = QFont(FUENTE, tam)
            caja = QFontMetrics(fuente).boundingRect(area, self._FLAGS, texto)
            if caja.height() <= alto_max:
                break
        return fuente, caja.size()

    def _geometria_burbuja(self):
        """Devuelve (rect del globo, fuente) o None si no hay globo."""
        if self._estado == "reposo":
            return None
        if self._estado == "login":
            return self._rect_login(), None
        if not self._texto:
            return None
        fuente, tam = self._medir_texto(self._texto_ajuste)
        ancho = max(tam.width(), 40) + 2 * RELLENO
        alto = tam.height() + 2 * RELLENO
        return QRectF(self._x_burbuja, self._y_burbuja, ancho, alto), fuente

    def _dibujar_burbuja(self, p, rect):
        borde = QColor(COLOR_BORDE_ERROR if self._estado == "error" else COLOR_BORDE)
        p.setPen(QPen(borde, 1.5))
        p.setBrush(QColor(*COLOR_FONDO))

        cuerpo = QPainterPath()
        cuerpo.addRoundedRect(rect, RADIO, RADIO)
        cy = rect.top() + min(rect.height() / 2, 30)

        if self._estado == "pensando":
            # Globo de pensamiento: cuerpo + circulitos hacia el personaje
            p.drawPath(cuerpo)
            p.drawEllipse(QPointF(rect.left() - 7, cy + 4), 5, 5)
            p.drawEllipse(QPointF(rect.left() - 15, cy + 10), 3, 3)
        else:
            cola = QPainterPath()
            cola.moveTo(rect.left() + 1, cy - 7)
            cola.lineTo(rect.left() - COLA, cy + 2)
            cola.lineTo(rect.left() + 1, cy + 9)
            cola.closeSubpath()
            p.drawPath(cuerpo.united(cola))

    # ------------------------------------------------------------ eventos
    def paintEvent(self, _evento):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)

        pm = self._pixmaps[self._estado]
        p.drawPixmap(0, self.height() - pm.height(), pm)

        datos = self._geometria_burbuja()
        if datos is None:
            return
        rect, fuente = datos
        self._dibujar_burbuja(p, rect)

        if self._estado == "login":
            return  # los campos de login son widgets hijos
        p.setPen(QColor(COLOR_TEXTO))
        p.setFont(fuente)
        area = rect.adjusted(RELLENO, RELLENO, -RELLENO, -RELLENO)
        p.drawText(area, self._FLAGS, self._texto)

    def contextMenuEvent(self, evento):
        menu = QMenu(self)
        menu.addAction("Salir", QApplication.quit)
        menu.exec(evento.globalPos())