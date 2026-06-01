
import os
import shutil
import sqlite3
from kivy.app import App

def obtener_ruta_db():
    app = App.get_running_app()
    ruta_destino = os.path.join(app.user_data_dir, "sistema_escritorio.db")
    ruta_origen = "sistema_escritorio.db"
    if not os.path.exists(ruta_destino):
        if os.path.exists(ruta_origen):
            shutil.copy(ruta_origen, ruta_destino)
            
    return ruta_destino

# 2. Función de conexión mejorada
def abrir_conexion():
    ruta = obtener_ruta_db()
    enlace = sqlite3.connect(ruta)
    # Activamos llaves foráneas, esto es crucial para tu base de datos relacional
    enlace.execute("PRAGMA foreign_keys = ON;")
    return enlace
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView

RUTA_BD = "sistema_escritorio.db"

# ── colores reutilizables ──────────────────────────────────────
COLOR_PRIMARIO   = (0.05, 0.40, 0.55, 1)
COLOR_SECUNDARIO = (0.10, 0.62, 0.47, 1)
COLOR_PELIGRO    = (0.75, 0.22, 0.17, 1)
COLOR_NEUTRO     = (0.25, 0.25, 0.30, 1)


def abrir_conexion():
    enlace = sqlite3.connect(RUTA_BD)
    enlace.execute("PRAGMA foreign_keys = ON")
    enlace.row_factory = sqlite3.Row
    return enlace


def crear_tablas():
    with abrir_conexion() as cn:
        cn.executescript("""
        CREATE TABLE IF NOT EXISTS programa (
            id_programa  INTEGER PRIMARY KEY AUTOINCREMENT,
            sigla        TEXT NOT NULL UNIQUE,
            titulo       TEXT NOT NULL,
            descripcion  TEXT
        );
        CREATE TABLE IF NOT EXISTS docente (
            id_docente   INTEGER PRIMARY KEY AUTOINCREMENT,
            clave_doc    TEXT NOT NULL UNIQUE,
            nombre       TEXT NOT NULL,
            paterno      TEXT NOT NULL,
            email        TEXT NOT NULL UNIQUE,
            area         TEXT
        );
        CREATE TABLE IF NOT EXISTS alumno (
            id_alumno    INTEGER PRIMARY KEY AUTOINCREMENT,
            matricula    TEXT    NOT NULL UNIQUE,
            nombre       TEXT    NOT NULL,
            paterno      TEXT    NOT NULL,
            email        TEXT    NOT NULL UNIQUE,
            nivel        INTEGER NOT NULL CHECK(nivel BETWEEN 1 AND 12),
            id_programa  INTEGER NOT NULL,
            FOREIGN KEY (id_programa) REFERENCES programa(id_programa) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS asignatura (
            id_asignatura INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo        TEXT    NOT NULL UNIQUE,
            titulo        TEXT    NOT NULL,
            unidades      INTEGER NOT NULL CHECK(unidades > 0),
            nivel         INTEGER NOT NULL CHECK(nivel BETWEEN 1 AND 12),
            id_programa   INTEGER NOT NULL,
            FOREIGN KEY (id_programa) REFERENCES programa(id_programa) ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS espacio (
            id_espacio  INTEGER PRIMARY KEY AUTOINCREMENT,
            referencia  TEXT    NOT NULL UNIQUE,
            bloque      TEXT    NOT NULL,
            aforo       INTEGER NOT NULL CHECK(aforo > 0),
            categoria   TEXT    NOT NULL CHECK(categoria IN ('aula','lab','taller','auditorio'))
        );
        CREATE TABLE IF NOT EXISTS ciclo (
            id_ciclo     INTEGER PRIMARY KEY AUTOINCREMENT,
            denominacion TEXT NOT NULL UNIQUE,
            inicio       TEXT NOT NULL,
            cierre       TEXT NOT NULL,
            fase         TEXT NOT NULL DEFAULT 'activo'
                         CHECK(fase IN ('activo','cerrado','planeado'))
        );
        CREATE TABLE IF NOT EXISTS seccion (
            id_seccion  INTEGER PRIMARY KEY AUTOINCREMENT,
            turno       TEXT    NOT NULL,
            id_docente  INTEGER NOT NULL,
            id_asignatura INTEGER NOT NULL,
            id_espacio  INTEGER NOT NULL,
            id_ciclo    INTEGER NOT NULL,
            FOREIGN KEY (id_docente)    REFERENCES docente(id_docente)       ON DELETE RESTRICT,
            FOREIGN KEY (id_asignatura) REFERENCES asignatura(id_asignatura) ON DELETE RESTRICT,
            FOREIGN KEY (id_espacio)    REFERENCES espacio(id_espacio)       ON DELETE RESTRICT,
            FOREIGN KEY (id_ciclo)      REFERENCES ciclo(id_ciclo)           ON DELETE RESTRICT
        );
        CREATE TABLE IF NOT EXISTS inscripcion (
            id_seccion INTEGER NOT NULL,
            id_alumno  INTEGER NOT NULL,
            PRIMARY KEY (id_seccion, id_alumno),
            FOREIGN KEY (id_seccion) REFERENCES seccion(id_seccion) ON DELETE CASCADE,
            FOREIGN KEY (id_alumno)  REFERENCES alumno(id_alumno)   ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS evaluacion (
            id_evaluacion INTEGER PRIMARY KEY AUTOINCREMENT,
            nota_parcial  REAL CHECK(nota_parcial BETWEEN 0 AND 100),
            nota_final    REAL CHECK(nota_final   BETWEEN 0 AND 100),
            comentario    TEXT,
            id_alumno     INTEGER NOT NULL,
            id_seccion    INTEGER NOT NULL,
            UNIQUE (id_alumno, id_seccion),
            FOREIGN KEY (id_alumno)  REFERENCES alumno(id_alumno)   ON DELETE CASCADE,
            FOREIGN KEY (id_seccion) REFERENCES seccion(id_seccion) ON DELETE CASCADE
        );
        """)


def notificar(encabezado, texto):
    cuerpo = BoxLayout(orientation="vertical", padding=12, spacing=12)
    cuerpo.add_widget(Label(text=texto, font_size=15))
    cerrar = Button(text="Aceptar", size_hint=(1, 0.38), font_size=15,
                    background_color=COLOR_PRIMARIO)
    modal = Popup(title=encabezado, content=cuerpo, size_hint=(0.82, 0.38))
    cerrar.bind(on_press=modal.dismiss)
    cuerpo.add_widget(cerrar)
    modal.open()


def pedir_confirmacion(encabezado, texto, accion):
    cuerpo = BoxLayout(orientation="vertical", padding=12, spacing=10)
    cuerpo.add_widget(Label(text=texto, font_size=14))
    fila = BoxLayout(orientation="horizontal", spacing=10, size_hint=(1, 0.38))
    modal = Popup(title=encabezado, content=cuerpo, size_hint=(0.84, 0.44))

    btn_ok = Button(text="Confirmar", font_size=14, background_color=COLOR_PELIGRO)
    btn_no = Button(text="Cancelar",  font_size=14, background_color=COLOR_NEUTRO)

    def ejecutar(inst):
        modal.dismiss()
        accion()

    btn_ok.bind(on_press=ejecutar)
    btn_no.bind(on_press=modal.dismiss)
    fila.add_widget(btn_no)
    fila.add_widget(btn_ok)
    cuerpo.add_widget(fila)
    modal.open()


# ══════════════════════════════════════════════════════════════════
#  PANTALLA DE ACCESO PRINCIPAL (CON LLAVE)
# ══════════════════════════════════════════════════════════════════
class PantallaInicio(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=35, spacing=18)

        self.etiqueta_claves = Label(
            text="Consultas: consulta123  |  Registros: registro123",
            font_size=12,
            size_hint=(1, 0.10),
            color=(0.95, 0.75, 0.2, 1)
        )
        raiz.add_widget(self.etiqueta_claves)

        raiz.add_widget(Label(text="Gestión Académica", font_size=28,
                              size_hint=(1, 0.25), color=(0.85, 0.95, 1, 1)))

        self.campo_clave = TextInput(
            hint_text="Ingresa clave de acceso",
            password=True,
            multiline=False,
            size_hint=(1, 0.13)
        )
        raiz.add_widget(self.campo_clave)

        self.btn_acceder = Button(
            text="Acceder",
            size_hint=(1, 0.13),
            font_size=16,
            background_color=COLOR_SECUNDARIO
        )
        self.btn_acceder.bind(on_press=self.validar_clave)
        raiz.add_widget(self.btn_acceder)

        self.btn_salir = Button(
            text="Salir del sistema",
            size_hint=(1, 0.13),
            font_size=16,
            background_color=COLOR_PELIGRO
        )
        self.btn_salir.bind(on_press=lambda x: App.get_running_app().stop())
        raiz.add_widget(self.btn_salir)

        raiz.add_widget(Label(size_hint=(1, 0.10)))
        self.add_widget(raiz)

    def validar_clave(self, inst):
        clave = self.campo_clave.text.strip()
        if clave == "consulta123":
            self.manager.current = "menu_consulta"
        elif clave == "registro123":
            self.manager.current = "menu_registro"
        else:
            notificar("Clave denegada", "La clave ingresada no es válida.")

    def on_enter(self):
        self.campo_clave.text = ""


# ══════════════════════════════════════════════════════════════════
#  PANTALLAS MENÚ: REGISTROS Y CONSULTAS
# ══════════════════════════════════════════════════════════════════
class PantallaMenuRegistro(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=20, spacing=8)
        raiz.add_widget(Label(text="Panel de Administración", font_size=22,
                              size_hint=(1, 0.10), color=(0.85, 0.95, 1, 1)))

        scroll = ScrollView(size_hint=(1, 0.78))
        contenedor = BoxLayout(orientation="vertical", spacing=8, size_hint_y=None)
        contenedor.bind(minimum_height=contenedor.setter('height'))

        secciones = [
            ("Programas Académicos",    "programas"),
            ("Planta Docente",          "docentes"),
            ("Alumnado",                "alumnos"),
            ("Catálogo de Materias",    "asignaturas"),
            ("Espacios / Aulas",        "espacios"),
            ("Ciclos Escolares",        "ciclos"),
            ("Secciones / Grupos",      "secciones"),
            ("Inscripciones a Grupos",  "inscripciones"),
            ("Registro de Notas",       "evaluaciones"),
        ]
        for etiqueta, destino in secciones:
            b = Button(text=etiqueta, size_hint_y=None, height=45, font_size=14,
                       background_color=COLOR_PRIMARIO)
            b.bind(on_press=lambda x, d=destino: setattr(self.manager, "current", d))
            contenedor.add_widget(b)
        scroll.add_widget(contenedor)
        raiz.add_widget(scroll)

        b_volver = Button(text="↩ Regresar", size_hint=(1, 0.09), font_size=15,
                         background_color=COLOR_NEUTRO)
        b_volver.bind(on_press=lambda x: setattr(self.manager, "current", "inicio"))
        raiz.add_widget(b_volver)
        self.add_widget(raiz)


class PantallaMenuConsulta(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=22, spacing=10)
        raiz.add_widget(Label(text="Menú de Consulta", font_size=24,
                              size_hint=(1, 0.18), color=(0.85, 0.95, 1, 1)))

        opciones = [
            ("Directorio de Alumnos",  "consulta_alumnos"),
            ("Directorio de Docentes", "consulta_docentes"),
            ("Horarios y Secciones",   "consulta_secciones"),
            ("Calificaciones",         "consulta_evaluaciones"),
        ]
        for etiqueta, destino in opciones:
            b = Button(text=etiqueta, size_hint=(1, 0.12), font_size=16,
                       background_color=COLOR_PRIMARIO)
            b.bind(on_press=lambda x, d=destino: setattr(self.manager, "current", d))
            raiz.add_widget(b)

        b_volver = Button(text="↩ Regresar", size_hint=(1, 0.12), font_size=16,
                         background_color=COLOR_NEUTRO)
        b_volver.bind(on_press=lambda x: setattr(self.manager, "current", "inicio"))
        raiz.add_widget(b_volver)
        self.add_widget(raiz)


# ══════════════════════════════════════════════════════════════════
#  PANTALLAS REGISTROS (ADMINISTRATIVAS)
# ══════════════════════════════════════════════════════════════════
class PantallaProgramas(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=18, spacing=8)
        raiz.add_widget(Label(text="Programas Académicos", font_size=24,
                              size_hint=(1, 0.07), color=(0.7, 1, 0.85, 1)))

        self.f_sigla = TextInput(hint_text="Sigla del programa (ej. IIA)", multiline=False, size_hint=(1, 0.07))
        self.f_tit   = TextInput(hint_text="Nombre completo del programa", multiline=False, size_hint=(1, 0.07))
        self.f_desc  = TextInput(hint_text="Descripción breve (opcional)", multiline=False, size_hint=(1, 0.07))

        btn_nuevo = Button(text="Registrar programa", size_hint=(1, 0.07), font_size=15, background_color=COLOR_SECUNDARIO)
        btn_nuevo.bind(on_press=self.guardar)

        for w in [self.f_sigla, self.f_tit, self.f_desc, btn_nuevo]:
            raiz.add_widget(w)

        raiz.add_widget(Label(text="— Eliminar programa —", font_size=12, size_hint=(1, 0.04), color=(0.8, 0.5, 0.5, 1)))
        self.f_baja = TextInput(hint_text="Sigla del programa a eliminar", multiline=False, size_hint=(1, 0.07))
        raiz.add_widget(self.f_baja)
        btn_baja = Button(text="Dar de baja", size_hint=(1, 0.07), font_size=15, background_color=COLOR_PELIGRO)
        btn_baja.bind(on_press=self.pedir_baja)
        raiz.add_widget(btn_baja)

        btn_listar = Button(text="Listar todos los programas", size_hint=(1, 0.07), font_size=15, background_color=COLOR_PRIMARIO)
        btn_listar.bind(on_press=self.listar)
        raiz.add_widget(btn_listar)

        scroll = ScrollView(size_hint=(1, 0.22))
        self.panel = Label(text="", font_size=12, size_hint_y=None, halign="left", valign="top")
        self.panel.bind(texture_size=lambda i, s: setattr(self.panel, "height", s[1]))
        self.panel.bind(width=lambda i, w: setattr(self.panel, "text_size", (w, None)))
        scroll.add_widget(self.panel)
        raiz.add_widget(scroll)

        btn_volver = Button(text="↩ Regresar", size_hint=(1, 0.07), font_size=15, background_color=COLOR_NEUTRO)
        btn_volver.bind(on_press=lambda x: setattr(self.manager, "current", "menu_registro"))
        raiz.add_widget(btn_volver)
        self.add_widget(raiz)

    def guardar(self, inst):
        sig  = self.f_sigla.text.strip().upper()
        tit  = self.f_tit.text.strip()
        desc = self.f_desc.text.strip()
        if not sig or not tit:
            notificar("Campos requeridos", "Sigla y nombre son obligatorios.")
            return
        try:
            with abrir_conexion() as cn:
                cn.execute("INSERT INTO programa (sigla, titulo, descripcion) VALUES (?,?,?)", (sig, tit, desc or None))
            for c in [self.f_sigla, self.f_tit, self.f_desc]:
                c.text = ""
            notificar("Registrado", "Programa guardado exitosamente.")
            self.listar(None)
        except sqlite3.IntegrityError:
            notificar("Duplicado", "Ya existe un programa con esa sigla.")

    def pedir_baja(self, inst):
        sig = self.f_baja.text.strip().upper()
        if not sig:
            notificar("Campo vacío", "Escribe la sigla del programa.")
            return
        with abrir_conexion() as cn:
            reg = cn.execute("SELECT titulo FROM programa WHERE sigla=?", (sig,)).fetchone()
        if not reg:
            notificar("No encontrado", f"No existe el programa con sigla '{sig}'.")
            return
        pedir_confirmacion("Confirmar baja", f"¿Eliminar el programa '{reg['titulo']}'?\nFallará si hay alumnos o materias vinculados.", lambda: self.eliminar(sig))

    def eliminar(self, sig):
        try:
            with abrir_conexion() as cn:
                cn.execute("DELETE FROM programa WHERE sigla=?", (sig,))
            self.f_baja.text = ""
            notificar("Eliminado", "Programa eliminado correctamente.")
            self.listar(None)
        except sqlite3.IntegrityError:
            notificar("Restringido", "No es posible eliminar: existen dependencias activas.")
        except Exception as e:
            notificar("Error", str(e))

    def listar(self, inst):
        try:
            with abrir_conexion() as cn:
                rows = cn.execute("SELECT * FROM programa ORDER BY titulo").fetchall()
            if not rows:
                self.panel.text = "Sin programas registrados."
                return
            txt = "Programas disponibles:\n\n"
            for i, r in enumerate(rows, 1):
                txt += f"{i}. [{r['sigla']}]  {r['titulo']}\n"
                if r['descripcion']:
                    txt += f"   {r['descripcion']}\n"
                txt += "\n"
            self.panel.text = txt
        except Exception as e:
            self.panel.text = f"Error: {e}"

    def on_enter(self):
        self.listar(None)


class PantallaDocentes(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=18, spacing=7)
        raiz.add_widget(Label(text="Planta Docente", font_size=24, size_hint=(1, 0.06), color=(0.7, 1, 0.85, 1)))

        self.f_clave = TextInput(hint_text="Clave del docente",  multiline=False, size_hint=(1, 0.07))
        self.f_nom   = TextInput(hint_text="Nombre(s)",          multiline=False, size_hint=(1, 0.07))
        self.f_pat   = TextInput(hint_text="Apellido paterno",   multiline=False, size_hint=(1, 0.07))
        self.f_mail  = TextInput(hint_text="Correo electrónico", multiline=False, size_hint=(1, 0.07))
        self.f_area  = TextInput(hint_text="Área de conocimiento (opcional)", multiline=False, size_hint=(1, 0.07))

        btn_nuevo = Button(text="Registrar docente", size_hint=(1, 0.07), font_size=15, background_color=COLOR_SECUNDARIO)
        btn_nuevo.bind(on_press=self.guardar)

        for w in [self.f_nom, self.f_pat, self.f_clave, self.f_mail, self.f_area, btn_nuevo]:
            raiz.add_widget(w)

        raiz.add_widget(Label(text="— Eliminar docente —", font_size=12, size_hint=(1, 0.04), color=(0.8, 0.5, 0.5, 1)))
        self.f_baja = TextInput(hint_text="Clave del docente a eliminar", multiline=False, size_hint=(1, 0.07))
        raiz.add_widget(self.f_baja)
        btn_baja = Button(text="Dar de baja", size_hint=(1, 0.07), font_size=15, background_color=COLOR_PELIGRO)
        btn_baja.bind(on_press=self.pedir_baja)
        raiz.add_widget(btn_baja)

        btn_listar = Button(text="Ver listado de docentes", size_hint=(1, 0.07), font_size=15, background_color=COLOR_PRIMARIO)
        btn_listar.bind(on_press=self.listar)
        raiz.add_widget(btn_listar)

        scroll = ScrollView(size_hint=(1, 0.22))
        self.panel = Label(text="", font_size=12, size_hint_y=None, halign="left", valign="top")
        self.panel.bind(texture_size=lambda i, s: setattr(self.panel, "height", s[1]))
        self.panel.bind(width=lambda i, w: setattr(self.panel, "text_size", (w, None)))
        scroll.add_widget(self.panel)
        raiz.add_widget(scroll)

        btn_volver = Button(text="↩ Regresar", size_hint=(1, 0.07), font_size=15, background_color=COLOR_NEUTRO)
        btn_volver.bind(on_press=lambda x: setattr(self.manager, "current", "menu_registro"))
        raiz.add_widget(btn_volver)
        self.add_widget(raiz)

    def guardar(self, inst):
        clave = self.f_clave.text.strip()
        nom   = self.f_nom.text.strip()
        pat   = self.f_pat.text.strip()
        mail  = self.f_mail.text.strip()
        area  = self.f_area.text.strip()
        if not all([clave, nom, pat, mail]):
            notificar("Campos requeridos", "Clave, nombre, apellido y correo son obligatorios.")
            return
        try:
            with abrir_conexion() as cn:
                cn.execute("INSERT INTO docente (clave_doc, nombre, paterno, email, area) VALUES (?,?,?,?,?)", (clave, nom, pat, mail, area or None))
            for c in [self.f_clave, self.f_nom, self.f_pat, self.f_mail, self.f_area]:
                c.text = ""
            notificar("Registrado", "Docente guardado exitosamente.")
            self.listar(None)
        except sqlite3.IntegrityError:
            notificar("Duplicado", "La clave o el correo ya están registrados.")

    def pedir_baja(self, inst):
        clave = self.f_baja.text.strip()
        if not clave:
            notificar("Campo vacío", "Escribe la clave del docente.")
            return
        with abrir_conexion() as cn:
            reg = cn.execute("SELECT nombre, paterno FROM docente WHERE clave_doc=?", (clave,)).fetchone()
        if not reg:
            notificar("No encontrado", f"No existe el docente con clave '{clave}'.")
            return
        pedir_confirmacion("Confirmar baja", f"¿Eliminar al docente '{reg['nombre']} {reg['paterno']}'?\nFallará si tiene secciones activas.", lambda: self.eliminar(clave))

    def eliminar(self, clave):
        try:
            with abrir_conexion() as cn:
                cn.execute("DELETE FROM docente WHERE clave_doc=?", (clave,))
            self.f_baja.text = ""
            notificar("Eliminado", "Docente eliminado correctamente.")
            self.listar(None)
        except sqlite3.IntegrityError:
            notificar("Restringido", "No es posible eliminar: tiene secciones asignadas.")
        except Exception as e:
            notificar("Error", str(e))

    def listar(self, inst):
        try:
            with abrir_conexion() as cn:
                rows = cn.execute("SELECT * FROM docente ORDER BY paterno").fetchall()
            if not rows:
                self.panel.text = "Sin docentes registrados."
                return
            txt = "Docentes activos:\n\n"
            for i, r in enumerate(rows, 1):
                txt += f"{i}. {r['nombre']} {r['paterno']}  [Clave: {r['clave_doc']}]\n"
                txt += f"   {r['area'] or 'Área no especificada'}\n\n"
            self.panel.text = txt
        except Exception as e:
            self.panel.text = f"Error: {e}"

    def on_enter(self):
        self.listar(None)


class PantallaAlumnos(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=18, spacing=7)
        raiz.add_widget(Label(text="Alumnado", font_size=24, size_hint=(1, 0.06), color=(0.7, 1, 0.85, 1)))

        self.f_mat  = TextInput(hint_text="Matrícula del alumno",    multiline=False, size_hint=(1, 0.07))
        self.f_nom  = TextInput(hint_text="Nombre(s)",               multiline=False, size_hint=(1, 0.07))
        self.f_pat  = TextInput(hint_text="Apellido paterno",        multiline=False, size_hint=(1, 0.07))
        self.f_mail = TextInput(hint_text="Correo electrónico",      multiline=False, size_hint=(1, 0.07))
        self.f_niv  = TextInput(hint_text="Nivel / Semestre (1-12)", multiline=False, size_hint=(1, 0.07))
        self.f_prog = TextInput(hint_text="ID de programa (ver lista)", multiline=False, size_hint=(1, 0.07))

        btn_nuevo = Button(text="Registrar alumno", size_hint=(1, 0.07), font_size=15, background_color=COLOR_SECUNDARIO)
        btn_nuevo.bind(on_press=self.guardar)

        for w in [self.f_mat, self.f_nom, self.f_pat, self.f_mail, self.f_niv, self.f_prog, btn_nuevo]:
            raiz.add_widget(w)

        raiz.add_widget(Label(text="— Eliminar alumno —", font_size=12, size_hint=(1, 0.04), color=(0.8, 0.5, 0.5, 1)))
        self.f_baja = TextInput(hint_text="Matrícula a eliminar", multiline=False, size_hint=(1, 0.07))
        raiz.add_widget(self.f_baja)
        btn_baja = Button(text="Dar de baja", size_hint=(1, 0.07), font_size=15, background_color=COLOR_PELIGRO)
        btn_baja.bind(on_press=self.pedir_baja)
        raiz.add_widget(btn_baja)

        btn_listar = Button(text="Ver todos los alumnos", size_hint=(1, 0.07), font_size=15, background_color=COLOR_PRIMARIO)
        btn_listar.bind(on_press=self.listar)
        raiz.add_widget(btn_listar)

        scroll = ScrollView(size_hint=(1, 0.30))
        self.panel = Label(text="", font_size=12, size_hint_y=None, halign="left", valign="top")
        self.panel.bind(texture_size=lambda i, s: setattr(self.panel, "height", s[1]))
        self.panel.bind(width=lambda i, w: setattr(self.panel, "text_size", (w, None)))
        scroll.add_widget(self.panel)
        raiz.add_widget(scroll)

        btn_volver = Button(text="↩ Regresar", size_hint=(1, 0.07), font_size=15, background_color=COLOR_NEUTRO)
        btn_volver.bind(on_press=lambda x: setattr(self.manager, "current", "menu_registro"))
        raiz.add_widget(btn_volver)
        self.add_widget(raiz)

    def guardar(self, inst):
        mat  = self.f_mat.text.strip()
        nom  = self.f_nom.text.strip()
        pat  = self.f_pat.text.strip()
        mail = self.f_mail.text.strip()
        niv  = self.f_niv.text.strip()
        prog = self.f_prog.text.strip()
        if not all([mat, nom, pat, mail, niv, prog]):
            notificar("Campos requeridos", "Todos los campos son obligatorios.")
            return
        try:
            niv_i  = int(niv)
            prog_i = int(prog)
            if not (1 <= niv_i <= 12):
                notificar("Valor inválido", "El nivel debe estar entre 1 y 12.")
                return
        except ValueError:
            notificar("Formato inválido", "Nivel e ID de programa deben ser números enteros.")
            return
        with abrir_conexion() as cn:
            existe = cn.execute("SELECT 1 FROM programa WHERE id_programa=?", (prog_i,)).fetchone()
        if not existe:
            notificar("No encontrado", f"El programa con ID {prog_i} no existe.")
            return
        try:
            with abrir_conexion() as cn:
                cn.execute("INSERT INTO alumno (matricula, nombre, paterno, email, nivel, id_programa) VALUES (?,?,?,?,?,?)", (mat, nom, pat, mail, niv_i, prog_i))
            for c in [self.f_mat, self.f_nom, self.f_pat, self.f_mail, self.f_niv, self.f_prog]:
                c.text = ""
            notificar("Registrado", "Alumno guardado exitosamente.")
            self.listar(None)
        except sqlite3.IntegrityError:
            notificar("Duplicado", "La matrícula o el correo ya están registrados.")

    def pedir_baja(self, inst):
        mat = self.f_baja.text.strip()
        if not mat:
            notificar("Campo vacío", "Escribe la matrícula del alumno.")
            return
        with abrir_conexion() as cn:
            reg = cn.execute("SELECT nombre, paterno FROM alumno WHERE matricula=?", (mat,)).fetchone()
        if not reg:
            notificar("No encontrado", f"No existe el alumno con matrícula '{mat}'.")
            return
        pedir_confirmacion("Confirmar baja", f"¿Dar de baja a '{reg['nombre']} {reg['paterno']}'?\nSe eliminarán también sus evaluaciones e inscripciones.", lambda: self.eliminar(mat))

    def eliminar(self, mat):
        try:
            with abrir_conexion() as cn:
                cn.execute("DELETE FROM alumno WHERE matricula=?", (mat,))
            self.f_baja.text = ""
            notificar("Eliminado", "Alumno eliminado correctamente.")
            self.listar(None)
        except Exception as e:
            notificar("Error", str(e))

    def listar(self, inst):
        try:
            with abrir_conexion() as cn:
                progs = cn.execute("SELECT id_programa, sigla, titulo FROM programa ORDER BY id_programa").fetchall()
                alumnos = cn.execute("""
                    SELECT a.matricula, a.nombre, a.paterno, a.nivel, p.titulo AS programa
                    FROM alumno a
                    JOIN programa p ON a.id_programa = p.id_programa
                    ORDER BY a.paterno
                """).fetchall()
            txt = "Programas disponibles (ID):\n"
            for p in progs:
                txt += f"  ID {p['id_programa']}: [{p['sigla']}] {p['titulo']}\n"
            txt += "\nAlumnos registrados:\n\n"
            if not alumnos:
                txt += "  Sin alumnos aún."
            else:
                for i, r in enumerate(alumnos, 1):
                    txt += f"{i}. {r['nombre']} {r['paterno']} [{r['matricula']}] Niv.{r['nivel']} — {r['programa']}\n"
            self.panel.text = txt
        except Exception as e:
            self.panel.text = f"Error: {e}"

    def on_enter(self):
        self.listar(None)


class PantallaAsignaturas(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=18, spacing=7)
        raiz.add_widget(Label(text="Catálogo de Materias", font_size=24, size_hint=(1, 0.06), color=(0.7, 1, 0.85, 1)))

        self.f_cod  = TextInput(hint_text="Código (ej. IIA301)",      multiline=False, size_hint=(1, 0.07))
        self.f_tit  = TextInput(hint_text="Nombre de la materia",     multiline=False, size_hint=(1, 0.07))
        self.f_uni  = TextInput(hint_text="Unidades de crédito",      multiline=False, size_hint=(1, 0.07))
        self.f_niv  = TextInput(hint_text="Nivel / Semestre (1-12)", multiline=False, size_hint=(1, 0.07))
        self.f_prog = TextInput(hint_text="ID de programa",           multiline=False, size_hint=(1, 0.07))

        btn_nuevo = Button(text="Agregar materia", size_hint=(1, 0.07), font_size=15, background_color=COLOR_SECUNDARIO)
        btn_nuevo.bind(on_press=self.guardar)

        for w in [self.f_cod, self.f_tit, self.f_uni, self.f_niv, self.f_prog, btn_nuevo]:
            raiz.add_widget(w)

        raiz.add_widget(Label(text="— Eliminar materia —", font_size=12, size_hint=(1, 0.04), color=(0.8, 0.5, 0.5, 1)))
        self.f_baja = TextInput(hint_text="Código de materia a eliminar", multiline=False, size_hint=(1, 0.07))
        raiz.add_widget(self.f_baja)
        btn_baja = Button(text="Eliminar", size_hint=(1, 0.07), font_size=15, background_color=COLOR_PELIGRO)
        btn_baja.bind(on_press=self.pedir_baja)
        raiz.add_widget(btn_baja)

        btn_listar = Button(text="Mostrar catálogo", size_hint=(1, 0.07), font_size=15, background_color=COLOR_PRIMARIO)
        btn_listar.bind(on_press=self.listar)
        raiz.add_widget(btn_listar)

        scroll = ScrollView(size_hint=(1, 0.22))
        self.panel = Label(text="", font_size=12, size_hint_y=None, halign="left", valign="top")
        self.panel.bind(texture_size=lambda i, s: setattr(self.panel, "height", s[1]))
        self.panel.bind(width=lambda i, w: setattr(self.panel, "text_size", (w, None)))
        scroll.add_widget(self.panel)
        raiz.add_widget(scroll)

        btn_volver = Button(text="↩ Regresar", size_hint=(1, 0.07), font_size=15, background_color=COLOR_NEUTRO)
        btn_volver.bind(on_press=lambda x: setattr(self.manager, "current", "menu_registro"))
        raiz.add_widget(btn_volver)
        self.add_widget(raiz)

    def guardar(self, inst):
        cod  = self.f_cod.text.strip().upper()
        tit  = self.f_tit.text.strip()
        uni  = self.f_uni.text.strip()
        niv  = self.f_niv.text.strip()
        prog = self.f_prog.text.strip()
        if not all([cod, tit, uni, niv, prog]):
            notificar("Campos requeridos", "Todos los campos son obligatorios.")
            return
        try:
            uni_i  = int(uni)
            niv_i  = int(niv)
            prog_i = int(prog)
        except ValueError:
            notificar("Formato inválido", "Unidades, nivel e ID deben ser enteros.")
            return
        with abrir_conexion() as cn:
            existe = cn.execute("SELECT 1 FROM programa WHERE id_programa=?", (prog_i,)).fetchone()
        if not existe:
            notificar("No encontrado", f"El programa con ID {prog_i} no existe.")
            return
        try:
            with abrir_conexion() as cn:
                cn.execute("INSERT INTO asignatura (codigo, titulo, unidades, nivel, id_programa) VALUES (?,?,?,?,?)", (cod, tit, uni_i, niv_i, prog_i))
            for c in [self.f_cod, self.f_tit, self.f_uni, self.f_niv, self.f_prog]:
                c.text = ""
            notificar("Registrado", "Materia agregada exitosamente.")
            self.listar(None)
        except sqlite3.IntegrityError:
            notificar("Duplicado", "Ese código de materia ya existe.")

    def pedir_baja(self, inst):
        cod = self.f_baja.text.strip().upper()
        if not cod:
            notificar("Campo vacío", "Escribe el código de la materia.")
            return
        with abrir_conexion() as cn:
            reg = cn.execute("SELECT titulo FROM asignatura WHERE codigo=?", (cod,)).fetchone()
        if not reg:
            notificar("No encontrado", f"No existe la materia con código '{cod}'.")
            return
        pedir_confirmacion("Confirmar eliminación", f"¿Eliminar la materia '{reg['titulo']}'?\nFallará si tiene secciones activas.", lambda: self.eliminar(cod))

    def eliminar(self, cod):
        try:
            with abrir_conexion() as cn:
                cn.execute("DELETE FROM asignatura WHERE codigo=?", (cod,))
            self.f_baja.text = ""
            notificar("Eliminado", "Materia eliminada correctamente.")
            self.listar(None)
        except sqlite3.IntegrityError:
            notificar("Restringido", "No se puede eliminar: tiene secciones activas.")
        except Exception as e:
            notificar("Error", str(e))

    def listar(self, inst):
        try:
            with abrir_conexion() as cn:
                progs = cn.execute("SELECT id_programa, sigla FROM programa ORDER BY id_programa").fetchall()
                rows = cn.execute("""
                    SELECT a.codigo, a.titulo, a.unidades, a.nivel, p.titulo AS programa
                    FROM asignatura a
                    JOIN programa p ON a.id_programa = p.id_programa
                    ORDER BY a.nivel, a.titulo
                """).fetchall()
            txt = "Programas (IDs):\n"
            for p in progs:
                txt += f"  ID {p['id_programa']}: {p['sigla']}\n"
            txt += "\nMaterias en catálogo:\n\n"
            if not rows:
                txt += "  Catálogo vacío."
            else:
                for r in rows:
                    txt += f"- [{r['codigo']}] {r['titulo']} (Sem. {r['nivel']}, Cred: {r['unidades']}) — {r['programa']}\n"
            self.panel.text = txt
        except Exception as e:
            self.panel.text = f"Error: {e}"

    def on_enter(self):
        self.listar(None)


# ══════════════════════════════════════════════════════════════════
#  PANTALLAS COMPLEMENTARIAS ADMINISTRATIVAS (MÓDULOS EN DESARROLLO)
# ══════════════════════════════════════════════════════════════════
class PantallaEspacios(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=18, spacing=7)
        raiz.add_widget(Label(text="Espacios / Aulas", font_size=24,
                              size_hint=(1, 0.06), color=(0.7, 1, 0.85, 1)))

        self.f_ref  = TextInput(hint_text="Referencia / Nombre (ej. A-101)",
                                multiline=False, size_hint=(1, 0.07))
        self.f_blq  = TextInput(hint_text="Bloque o edificio (ej. Bloque A)",
                                multiline=False, size_hint=(1, 0.07))
        self.f_afo  = TextInput(hint_text="Aforo / Capacidad (número)",
                                multiline=False, size_hint=(1, 0.07))
        self.f_cat  = TextInput(hint_text="Categoría: aula | lab | taller | auditorio",
                                multiline=False, size_hint=(1, 0.07))

        btn_nuevo = Button(text="Registrar espacio", size_hint=(1, 0.07),
                           font_size=15, background_color=COLOR_SECUNDARIO)
        btn_nuevo.bind(on_press=self.guardar)

        for w in [self.f_ref, self.f_blq, self.f_afo, self.f_cat, btn_nuevo]:
            raiz.add_widget(w)

        raiz.add_widget(Label(text="— Eliminar espacio —", font_size=12,
                              size_hint=(1, 0.04), color=(0.8, 0.5, 0.5, 1)))
        self.f_baja = TextInput(hint_text="Referencia del espacio a eliminar",
                                multiline=False, size_hint=(1, 0.07))
        raiz.add_widget(self.f_baja)
        btn_baja = Button(text="Eliminar espacio", size_hint=(1, 0.07), font_size=15,
                          background_color=COLOR_PELIGRO)
        btn_baja.bind(on_press=self.pedir_baja)
        raiz.add_widget(btn_baja)

        btn_listar = Button(text="Ver todos los espacios", size_hint=(1, 0.07),
                            font_size=15, background_color=COLOR_PRIMARIO)
        btn_listar.bind(on_press=self.listar)
        raiz.add_widget(btn_listar)

        scroll = ScrollView(size_hint=(1, 0.22))
        self.panel = Label(text="", font_size=12, size_hint_y=None,
                           halign="left", valign="top")
        self.panel.bind(texture_size=lambda i, s: setattr(self.panel, "height", s[1]))
        self.panel.bind(width=lambda i, w: setattr(self.panel, "text_size", (w, None)))
        scroll.add_widget(self.panel)
        raiz.add_widget(scroll)

        btn_volver = Button(text="↩ Regresar", size_hint=(1, 0.07), font_size=15,
                            background_color=COLOR_NEUTRO)
        btn_volver.bind(on_press=lambda x: setattr(self.manager, "current", "menu_registro"))
        raiz.add_widget(btn_volver)
        self.add_widget(raiz)

    def guardar(self, inst):
        ref = self.f_ref.text.strip()
        blq = self.f_blq.text.strip()
        afo = self.f_afo.text.strip()
        cat = self.f_cat.text.strip().lower()
        if not all([ref, blq, afo, cat]):
            notificar("Campos requeridos", "Todos los campos son obligatorios.")
            return
        if cat not in ("aula", "lab", "taller", "auditorio"):
            notificar("Categoría inválida",
                      "Escribe una de estas:\naula | lab | taller | auditorio")
            return
        try:
            afo_i = int(afo)
            if afo_i <= 0:
                notificar("Valor inválido", "El aforo debe ser mayor a 0.")
                return
        except ValueError:
            notificar("Formato inválido", "El aforo debe ser un número entero.")
            return
        try:
            with abrir_conexion() as cn:
                cn.execute(
                    "INSERT INTO espacio (referencia, bloque, aforo, categoria) VALUES (?,?,?,?)",
                    (ref, blq, afo_i, cat)
                )
            for c in [self.f_ref, self.f_blq, self.f_afo, self.f_cat]:
                c.text = ""
            notificar("Registrado", "Espacio guardado exitosamente.")
            self.listar(None)
        except sqlite3.IntegrityError:
            notificar("Duplicado", "Ya existe un espacio con esa referencia.")

    def pedir_baja(self, inst):
        ref = self.f_baja.text.strip()
        if not ref:
            notificar("Campo vacío", "Escribe la referencia del espacio.")
            return
        with abrir_conexion() as cn:
            reg = cn.execute("SELECT id_espacio FROM espacio WHERE referencia=?",
                             (ref,)).fetchone()
        if not reg:
            notificar("No encontrado", f"No existe el espacio '{ref}'.")
            return
        pedir_confirmacion(
            "Confirmar eliminación",
            f"¿Eliminar el espacio '{ref}'?\nFallará si tiene secciones asignadas.",
            lambda: self.eliminar(ref)
        )

    def eliminar(self, ref):
        try:
            with abrir_conexion() as cn:
                cn.execute("DELETE FROM espacio WHERE referencia=?", (ref,))
            self.f_baja.text = ""
            notificar("Eliminado", "Espacio eliminado correctamente.")
            self.listar(None)
        except sqlite3.IntegrityError:
            notificar("Restringido", "No se puede eliminar: tiene secciones asignadas.")
        except Exception as e:
            notificar("Error", str(e))

    def listar(self, inst):
        try:
            with abrir_conexion() as cn:
                rows = cn.execute(
                    "SELECT id_espacio, referencia, bloque, aforo, categoria "
                    "FROM espacio ORDER BY bloque, referencia"
                ).fetchall()
            if not rows:
                self.panel.text = "Sin espacios registrados."
                return
            txt = "Espacios disponibles:\n\n"
            for r in rows:
                txt += (f"ID {r['id_espacio']}  [{r['referencia']}]  "
                        f"{r['bloque']}  —  {r['categoria'].upper()}  "
                        f"(aforo: {r['aforo']})\n")
            self.panel.text = txt
        except Exception as e:
            self.panel.text = f"Error: {e}"

    def on_enter(self):
        self.listar(None)

class PantallaCiclos(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=18, spacing=7)
        raiz.add_widget(Label(text="Ciclos Escolares", font_size=24,
                              size_hint=(1, 0.06), color=(0.7, 1, 0.85, 1)))

        self.f_den  = TextInput(hint_text="Denominación (ej. 2025-1)",
                                multiline=False, size_hint=(1, 0.07))
        self.f_ini  = TextInput(hint_text="Fecha de inicio (ej. 2025-01-15)",
                                multiline=False, size_hint=(1, 0.07))
        self.f_cie  = TextInput(hint_text="Fecha de cierre (ej. 2025-06-30)",
                                multiline=False, size_hint=(1, 0.07))
        self.f_fase = TextInput(hint_text="Fase: activo | cerrado | planeado",
                                multiline=False, size_hint=(1, 0.07))

        btn_nuevo = Button(text="Registrar ciclo", size_hint=(1, 0.07),
                           font_size=15, background_color=COLOR_SECUNDARIO)
        btn_nuevo.bind(on_press=self.guardar)

        for w in [self.f_den, self.f_ini, self.f_cie, self.f_fase, btn_nuevo]:
            raiz.add_widget(w)

        raiz.add_widget(Label(text="— Eliminar ciclo —", font_size=12,
                              size_hint=(1, 0.04), color=(0.8, 0.5, 0.5, 1)))
        self.f_baja = TextInput(hint_text="Denominación del ciclo a eliminar",
                                multiline=False, size_hint=(1, 0.07))
        raiz.add_widget(self.f_baja)
        btn_baja = Button(text="Eliminar ciclo", size_hint=(1, 0.07), font_size=15,
                          background_color=COLOR_PELIGRO)
        btn_baja.bind(on_press=self.pedir_baja)
        raiz.add_widget(btn_baja)

        btn_listar = Button(text="Ver todos los ciclos", size_hint=(1, 0.07),
                            font_size=15, background_color=COLOR_PRIMARIO)
        btn_listar.bind(on_press=self.listar)
        raiz.add_widget(btn_listar)

        scroll = ScrollView(size_hint=(1, 0.22))
        self.panel = Label(text="", font_size=12, size_hint_y=None,
                           halign="left", valign="top")
        self.panel.bind(texture_size=lambda i, s: setattr(self.panel, "height", s[1]))
        self.panel.bind(width=lambda i, w: setattr(self.panel, "text_size", (w, None)))
        scroll.add_widget(self.panel)
        raiz.add_widget(scroll)

        btn_volver = Button(text="↩ Regresar", size_hint=(1, 0.07), font_size=15,
                            background_color=COLOR_NEUTRO)
        btn_volver.bind(on_press=lambda x: setattr(self.manager, "current", "menu_registro"))
        raiz.add_widget(btn_volver)
        self.add_widget(raiz)

    def guardar(self, inst):
        den  = self.f_den.text.strip()
        ini  = self.f_ini.text.strip()
        cie  = self.f_cie.text.strip()
        fase = self.f_fase.text.strip().lower()
        if not all([den, ini, cie, fase]):
            notificar("Campos requeridos", "Todos los campos son obligatorios.")
            return
        if fase not in ("activo", "cerrado", "planeado"):
            notificar("Fase inválida",
                      "Escribe una de estas:\nactivo | cerrado | planeado")
            return
        try:
            with abrir_conexion() as cn:
                cn.execute(
                    "INSERT INTO ciclo (denominacion, inicio, cierre, fase) VALUES (?,?,?,?)",
                    (den, ini, cie, fase)
                )
            for c in [self.f_den, self.f_ini, self.f_cie, self.f_fase]:
                c.text = ""
            notificar("Registrado", "Ciclo guardado exitosamente.")
            self.listar(None)
        except sqlite3.IntegrityError:
            notificar("Duplicado", "Ya existe un ciclo con esa denominación.")

    def pedir_baja(self, inst):
        den = self.f_baja.text.strip()
        if not den:
            notificar("Campo vacío", "Escribe la denominación del ciclo.")
            return
        with abrir_conexion() as cn:
            reg = cn.execute("SELECT id_ciclo FROM ciclo WHERE denominacion=?",
                             (den,)).fetchone()
        if not reg:
            notificar("No encontrado", f"No existe el ciclo '{den}'.")
            return
        pedir_confirmacion(
            "Confirmar eliminación",
            f"¿Eliminar el ciclo '{den}'?\nFallará si tiene secciones asignadas.",
            lambda: self.eliminar(den)
        )

    def eliminar(self, den):
        try:
            with abrir_conexion() as cn:
                cn.execute("DELETE FROM ciclo WHERE denominacion=?", (den,))
            self.f_baja.text = ""
            notificar("Eliminado", "Ciclo eliminado correctamente.")
            self.listar(None)
        except sqlite3.IntegrityError:
            notificar("Restringido", "No se puede eliminar: tiene secciones asignadas.")
        except Exception as e:
            notificar("Error", str(e))

    def listar(self, inst):
        try:
            with abrir_conexion() as cn:
                rows = cn.execute(
                    "SELECT id_ciclo, denominacion, inicio, cierre, fase "
                    "FROM ciclo ORDER BY inicio DESC"
                ).fetchall()
            if not rows:
                self.panel.text = "Sin ciclos registrados."
                return
            txt = "Ciclos escolares:\n\n"
            for r in rows:
                txt += (f"ID {r['id_ciclo']}  [{r['denominacion']}]  "
                        f"{r['inicio']} → {r['cierre']}  "
                        f"({r['fase'].upper()})\n")
            self.panel.text = txt
        except Exception as e:
            self.panel.text = f"Error: {e}"

    def on_enter(self):
        self.listar(None)


# ══════════════════════════════════════════════════════════════════
#  PANTALLA  SECCIONES
# ══════════════════════════════════════════════════════════════════
class PantallaSecciones(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=18, spacing=7)
        raiz.add_widget(Label(text="Secciones / Grupos", font_size=24,
                              size_hint=(1, 0.06), color=(0.7, 1, 0.85, 1)))

        self.f_doc = TextInput(hint_text="ID del docente",    multiline=False, size_hint=(1, 0.07))
        self.f_asi = TextInput(hint_text="ID de asignatura",  multiline=False, size_hint=(1, 0.07))
        self.f_esp = TextInput(hint_text="ID de espacio",     multiline=False, size_hint=(1, 0.07))
        self.f_cic = TextInput(hint_text="ID del ciclo",      multiline=False, size_hint=(1, 0.07))
        self.f_tur = TextInput(hint_text="Turno (ej. Mar-Jue 10:00-12:00)",
                               multiline=False, size_hint=(1, 0.07))

        btn_nuevo = Button(text="Crear sección", size_hint=(1, 0.07),
                           font_size=15, background_color=COLOR_SECUNDARIO)
        btn_nuevo.bind(on_press=self.guardar)

        for w in [self.f_doc, self.f_asi, self.f_esp, self.f_cic, self.f_tur, btn_nuevo]:
            raiz.add_widget(w)

        raiz.add_widget(Label(text="— Eliminar sección —", font_size=12,
                              size_hint=(1, 0.04), color=(0.8, 0.5, 0.5, 1)))
        self.f_baja = TextInput(hint_text="ID de la sección a eliminar",
                                multiline=False, size_hint=(1, 0.07))
        raiz.add_widget(self.f_baja)
        btn_baja = Button(text="Eliminar sección", size_hint=(1, 0.07), font_size=15,
                          background_color=COLOR_PELIGRO)
        btn_baja.bind(on_press=self.pedir_baja)
        raiz.add_widget(btn_baja)

        btn_listar = Button(text="Ver secciones e IDs", size_hint=(1, 0.07),
                            font_size=15, background_color=COLOR_PRIMARIO)
        btn_listar.bind(on_press=self.listar)
        raiz.add_widget(btn_listar)

        scroll = ScrollView(size_hint=(1, 0.22))
        self.panel = Label(text="", font_size=11, size_hint_y=None,
                           halign="left", valign="top")
        self.panel.bind(texture_size=lambda i, s: setattr(self.panel, "height", s[1]))
        self.panel.bind(width=lambda i, w: setattr(self.panel, "text_size", (w, None)))
        scroll.add_widget(self.panel)
        raiz.add_widget(scroll)

        btn_volver = Button(text="↩ Regresar", size_hint=(1, 0.07), font_size=15,
                            background_color=COLOR_NEUTRO)
        btn_volver.bind(on_press=lambda x: setattr(self.manager, "current", "menu_registro"))
        raiz.add_widget(btn_volver)
        self.add_widget(raiz)

    def guardar(self, inst):
        id_d = self.f_doc.text.strip()
        id_a = self.f_asi.text.strip()
        id_e = self.f_esp.text.strip()
        id_c = self.f_cic.text.strip()
        tur  = self.f_tur.text.strip()
        if not all([id_d, id_a, id_e, id_c, tur]):
            notificar("Campos requeridos", "Todos los campos son obligatorios.")
            return
        try:
            id_d_i = int(id_d); id_a_i = int(id_a)
            id_e_i = int(id_e); id_c_i = int(id_c)
        except ValueError:
            notificar("Formato inválido", "Los IDs deben ser números enteros.")
            return
        with abrir_conexion() as cn:
            ok_d = cn.execute("SELECT 1 FROM docente    WHERE id_docente=?",    (id_d_i,)).fetchone()
            ok_a = cn.execute("SELECT 1 FROM asignatura WHERE id_asignatura=?", (id_a_i,)).fetchone()
            ok_e = cn.execute("SELECT 1 FROM espacio    WHERE id_espacio=?",    (id_e_i,)).fetchone()
            ok_c = cn.execute("SELECT 1 FROM ciclo      WHERE id_ciclo=?",      (id_c_i,)).fetchone()
        if not all([ok_d, ok_a, ok_e, ok_c]):
            notificar("ID inválido", "Uno o más IDs no existen.\nUsa 'Ver secciones e IDs' para verificar.")
            return
        try:
            with abrir_conexion() as cn:
                cn.execute(
                    "INSERT INTO seccion (turno, id_docente, id_asignatura, id_espacio, id_ciclo) "
                    "VALUES (?,?,?,?,?)",
                    (tur, id_d_i, id_a_i, id_e_i, id_c_i)
                )
            for c in [self.f_doc, self.f_asi, self.f_esp, self.f_cic, self.f_tur]:
                c.text = ""
            notificar("Creado", "Sección creada exitosamente.")
            self.listar(None)
        except Exception as e:
            notificar("Error", str(e))

    def pedir_baja(self, inst):
        id_s = self.f_baja.text.strip()
        if not id_s:
            notificar("Campo vacío", "Escribe el ID de la sección.")
            return
        try:
            id_s_i = int(id_s)
        except ValueError:
            notificar("Formato inválido", "El ID debe ser un número entero.")
            return
        with abrir_conexion() as cn:
            reg = cn.execute("""
                SELECT a.titulo AS materia, d.nombre||' '||d.paterno AS docente
                FROM seccion s
                JOIN asignatura a ON s.id_asignatura = a.id_asignatura
                JOIN docente    d ON s.id_docente    = d.id_docente
                WHERE s.id_seccion=?
            """, (id_s_i,)).fetchone()
        if not reg:
            notificar("No encontrado", f"No existe la sección con ID {id_s_i}.")
            return
        pedir_confirmacion(
            "Confirmar eliminación",
            f"¿Eliminar sección [{id_s}]\n{reg['materia']} – {reg['docente']}?\n"
            "Se borrarán también inscripciones y evaluaciones.",
            lambda: self.eliminar(id_s_i)
        )

    def eliminar(self, id_sec):
        try:
            with abrir_conexion() as cn:
                cn.execute("DELETE FROM seccion WHERE id_seccion=?", (id_sec,))
            self.f_baja.text = ""
            notificar("Eliminado", "Sección eliminada correctamente.")
            self.listar(None)
        except Exception as e:
            notificar("Error", str(e))

    def listar(self, inst):
        try:
            with abrir_conexion() as cn:
                docentes  = cn.execute("SELECT id_docente, nombre, paterno FROM docente ORDER BY id_docente").fetchall()
                asignat   = cn.execute("SELECT id_asignatura, codigo FROM asignatura ORDER BY id_asignatura").fetchall()
                espacios  = cn.execute("SELECT id_espacio, referencia FROM espacio ORDER BY id_espacio").fetchall()
                ciclos    = cn.execute("SELECT id_ciclo, denominacion FROM ciclo ORDER BY id_ciclo").fetchall()
                secciones = cn.execute("""
                    SELECT s.id_seccion, a.titulo AS materia,
                           d.nombre||' '||d.paterno AS docente,
                           e.referencia AS espacio, c.denominacion AS ciclo, s.turno
                    FROM seccion s
                    JOIN asignatura a ON s.id_asignatura = a.id_asignatura
                    JOIN docente    d ON s.id_docente    = d.id_docente
                    JOIN espacio    e ON s.id_espacio    = e.id_espacio
                    JOIN ciclo      c ON s.id_ciclo      = c.id_ciclo
                """).fetchall()

            txt  = "Docentes: "  + " | ".join([f"ID{r['id_docente']}:{r['nombre']}"      for r in docentes])  + "\n"
            txt += "Materias: "  + " | ".join([f"ID{r['id_asignatura']}:{r['codigo']}"   for r in asignat])   + "\n"
            txt += "Espacios: "  + " | ".join([f"ID{r['id_espacio']}:{r['referencia']}"  for r in espacios])  + "\n"
            txt += "Ciclos: "    + " | ".join([f"ID{r['id_ciclo']}:{r['denominacion']}"  for r in ciclos])    + "\n\n"
            txt += "Secciones registradas:\n"
            if not secciones:
                txt += "  Sin secciones aún."
            else:
                for s in secciones:
                    txt += f"  [{s['id_seccion']}] {s['materia']} | {s['docente']} | {s['turno']}\n"
            self.panel.text = txt
        except Exception as e:
            self.panel.text = f"Error: {e}"

    def on_enter(self):
        self.listar(None)


# ══════════════════════════════════════════════════════════════════
#  PANTALLA  INSCRIPCIONES
# ══════════════════════════════════════════════════════════════════
class PantallaInscripciones(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=18, spacing=6)
        raiz.add_widget(Label(text="Inscripciones a Grupos", font_size=24,
                              size_hint=(1, 0.06), color=(0.7, 1, 0.85, 1)))

        raiz.add_widget(Label(text="— Inscribir alumno a un grupo —", font_size=13,
                              size_hint=(1, 0.04), color=(0.7, 0.9, 1, 1)))

        self.f_mat_insc = TextInput(hint_text="Matrícula del alumno",
                                    multiline=False, size_hint=(1, 0.07))
        self.f_sec_insc = TextInput(hint_text="ID de la sección/grupo",
                                    multiline=False, size_hint=(1, 0.07))
        raiz.add_widget(self.f_mat_insc)
        raiz.add_widget(self.f_sec_insc)

        btn_inscribir = Button(text="Inscribir alumno", size_hint=(1, 0.07),
                               font_size=15, background_color=COLOR_SECUNDARIO)
        btn_inscribir.bind(on_press=self.inscribir)
        raiz.add_widget(btn_inscribir)

        raiz.add_widget(Label(text="— Eliminar inscripción —", font_size=13,
                              size_hint=(1, 0.04), color=(0.8, 0.5, 0.5, 1)))

        self.f_mat_baja = TextInput(hint_text="Matrícula del alumno",
                                    multiline=False, size_hint=(1, 0.07))
        self.f_sec_baja = TextInput(hint_text="ID de la sección/grupo",
                                    multiline=False, size_hint=(1, 0.07))
        raiz.add_widget(self.f_mat_baja)
        raiz.add_widget(self.f_sec_baja)

        btn_desinscribir = Button(text="Eliminar inscripción", size_hint=(1, 0.07),
                                  font_size=15, background_color=COLOR_PELIGRO)
        btn_desinscribir.bind(on_press=self.pedir_baja)
        raiz.add_widget(btn_desinscribir)

        raiz.add_widget(Label(text="— Ver alumnos de un grupo —", font_size=13,
                              size_hint=(1, 0.04), color=(0.7, 0.9, 1, 1)))

        self.f_sec_ver = TextInput(hint_text="ID de la sección/grupo",
                                   multiline=False, size_hint=(1, 0.07))
        raiz.add_widget(self.f_sec_ver)

        btn_ver = Button(text="Mostrar alumnos", size_hint=(1, 0.07),
                         font_size=15, background_color=COLOR_PRIMARIO)
        btn_ver.bind(on_press=self.ver_alumnos)
        raiz.add_widget(btn_ver)

        scroll = ScrollView(size_hint=(1, 0.22))
        self.panel = Label(text="", font_size=12, size_hint_y=None,
                           halign="left", valign="top")
        self.panel.bind(texture_size=lambda i, s: setattr(self.panel, "height", s[1]))
        self.panel.bind(width=lambda i, w: setattr(self.panel, "text_size", (w, None)))
        scroll.add_widget(self.panel)
        raiz.add_widget(scroll)

        btn_volver = Button(text="↩ Regresar", size_hint=(1, 0.07), font_size=15,
                            background_color=COLOR_NEUTRO)
        btn_volver.bind(on_press=lambda x: setattr(self.manager, "current", "menu_registro"))
        raiz.add_widget(btn_volver)
        self.add_widget(raiz)

    def inscribir(self, inst):
        mat = self.f_mat_insc.text.strip()
        sec = self.f_sec_insc.text.strip()
        if not mat or not sec:
            notificar("Campos vacíos", "Ingresa matrícula e ID de sección.")
            return
        try:
            sec_i = int(sec)
        except ValueError:
            notificar("Formato inválido", "El ID de sección debe ser entero.")
            return

        with abrir_conexion() as cn:
            al = cn.execute("SELECT id_alumno, nombre, paterno FROM alumno WHERE matricula=?",
                            (mat,)).fetchone()
            sec_ok = cn.execute("""
                SELECT s.id_seccion, a.titulo AS materia
                FROM seccion s
                JOIN asignatura a ON s.id_asignatura = a.id_asignatura
                WHERE s.id_seccion=?
            """, (sec_i,)).fetchone()

        if not al:
            notificar("No encontrado", f"No existe el alumno con matrícula '{mat}'.")
            return
        if not sec_ok:
            notificar("No encontrado", f"No existe la sección con ID {sec_i}.")
            return

        try:
            with abrir_conexion() as cn:
                cn.execute("INSERT INTO inscripcion (id_seccion, id_alumno) VALUES (?,?)",
                           (sec_i, al['id_alumno']))
            self.f_mat_insc.text = ""
            self.f_sec_insc.text = ""
            notificar("Inscrito",
                      f"{al['nombre']} {al['paterno']}\ninscrito en '{sec_ok['materia']}'.")
        except sqlite3.IntegrityError:
            notificar("Ya inscrito", "El alumno ya está inscrito en esa sección.")
        except Exception as e:
            notificar("Error", str(e))

    def pedir_baja(self, inst):
        mat = self.f_mat_baja.text.strip()
        sec = self.f_sec_baja.text.strip()
        if not mat or not sec:
            notificar("Campos vacíos", "Ingresa matrícula e ID de sección.")
            return
        try:
            sec_i = int(sec)
        except ValueError:
            notificar("Formato inválido", "El ID de sección debe ser entero.")
            return

        with abrir_conexion() as cn:
            reg = cn.execute("""
                SELECT al.nombre, al.paterno, asig.titulo AS materia
                FROM inscripcion ins
                JOIN alumno     al   ON ins.id_alumno  = al.id_alumno
                JOIN seccion    s    ON ins.id_seccion = s.id_seccion
                JOIN asignatura asig ON s.id_asignatura = asig.id_asignatura
                WHERE al.matricula=? AND ins.id_seccion=?
            """, (mat, sec_i)).fetchone()

        if not reg:
            notificar("No encontrado",
                      f"No hay inscripción para matrícula '{mat}' en sección {sec_i}.")
            return

        pedir_confirmacion(
            "Confirmar eliminación",
            f"¿Eliminar inscripción de\n{reg['nombre']} {reg['paterno']}\nen '{reg['materia']}'?",
            lambda: self.eliminar(mat, sec_i)
        )

    def eliminar(self, mat, sec_i):
        try:
            with abrir_conexion() as cn:
                cn.execute("""
                    DELETE FROM inscripcion
                    WHERE id_alumno = (SELECT id_alumno FROM alumno WHERE matricula=?)
                      AND id_seccion = ?
                """, (mat, sec_i))
            self.f_mat_baja.text = ""
            self.f_sec_baja.text = ""
            notificar("Eliminado", "Inscripción eliminada correctamente.")
        except Exception as e:
            notificar("Error", str(e))

    def ver_alumnos(self, inst):
        sec = self.f_sec_ver.text.strip()
        if not sec:
            notificar("Campo vacío", "Ingresa el ID de la sección.")
            return
        try:
            sec_i = int(sec)
        except ValueError:
            notificar("Formato inválido", "El ID de sección debe ser entero.")
            return

        try:
            with abrir_conexion() as cn:
                info = cn.execute("""
                    SELECT a.titulo AS materia,
                           d.nombre||' '||d.paterno AS docente,
                           c.denominacion AS ciclo,
                           e.referencia AS espacio
                    FROM seccion s
                    JOIN asignatura a ON s.id_asignatura = a.id_asignatura
                    JOIN docente    d ON s.id_docente    = d.id_docente
                    JOIN ciclo      c ON s.id_ciclo      = c.id_ciclo
                    JOIN espacio    e ON s.id_espacio    = e.id_espacio
                    WHERE s.id_seccion=?
                """, (sec_i,)).fetchone()

                if not info:
                    self.panel.text = f"No existe la sección con ID {sec_i}."
                    return

                alumnos = cn.execute("""
                    SELECT al.matricula, al.nombre, al.paterno, al.email
                    FROM inscripcion ins
                    JOIN alumno al ON ins.id_alumno = al.id_alumno
                    WHERE ins.id_seccion = ?
                    ORDER BY al.paterno, al.nombre
                """, (sec_i,)).fetchall()

            txt  = f"Grupo [{sec_i}]  {info['materia']}\n"
            txt += f"Docente: {info['docente']}\n"
            txt += f"Ciclo: {info['ciclo']}  |  Espacio: {info['espacio']}\n"
            txt += "─" * 40 + "\n"

            if not alumnos:
                txt += "Sin alumnos inscritos."
            else:
                txt += f"Alumnos inscritos: {len(alumnos)}\n\n"
                for i, al in enumerate(alumnos, 1):
                    txt += f"{i}. {al['paterno']}, {al['nombre']}  [{al['matricula']}]\n"
                    txt += f"   {al['email']}\n"
            self.panel.text = txt
        except Exception as e:
            self.panel.text = f"Error: {e}"

    def on_enter(self):
        self.panel.text = "Usa los campos de arriba para inscribir,\neliminar o consultar alumnos de un grupo."


# ══════════════════════════════════════════════════════════════════
#  PANTALLA  EVALUACIONES
# ══════════════════════════════════════════════════════════════════
class PantallaEvaluaciones(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=18, spacing=7)
        raiz.add_widget(Label(text="Registro de Notas", font_size=24,
                              size_hint=(1, 0.06), color=(0.7, 1, 0.85, 1)))

        raiz.add_widget(Label(text="— Capturar / Actualizar nota —", font_size=13,
                              size_hint=(1, 0.04), color=(0.7, 0.9, 1, 1)))

        self.f_mat  = TextInput(hint_text="Matrícula del alumno",   multiline=False, size_hint=(1, 0.07))
        self.f_sec  = TextInput(hint_text="ID de sección",          multiline=False, size_hint=(1, 0.07))
        self.f_parc = TextInput(hint_text="Nota parcial (0-100)",   multiline=False, size_hint=(1, 0.07))
        self.f_fin  = TextInput(hint_text="Nota final   (0-100)",   multiline=False, size_hint=(1, 0.07))
        self.f_com  = TextInput(hint_text="Comentario (opcional)",  multiline=False, size_hint=(1, 0.07))

        btn_cap = Button(text="Guardar nota", size_hint=(1, 0.07),
                         font_size=15, background_color=COLOR_SECUNDARIO)
        btn_cap.bind(on_press=self.guardar)

        for w in [self.f_mat, self.f_sec, self.f_parc, self.f_fin, self.f_com, btn_cap]:
            raiz.add_widget(w)

        raiz.add_widget(Label(text="— Eliminar nota —", font_size=13,
                              size_hint=(1, 0.04), color=(0.8, 0.5, 0.5, 1)))
        self.f_baja_mat = TextInput(hint_text="Matrícula del alumno", multiline=False, size_hint=(1, 0.07))
        self.f_baja_sec = TextInput(hint_text="ID de sección",        multiline=False, size_hint=(1, 0.07))
        raiz.add_widget(self.f_baja_mat)
        raiz.add_widget(self.f_baja_sec)
        btn_baja = Button(text="Eliminar nota", size_hint=(1, 0.07), font_size=15,
                          background_color=COLOR_PELIGRO)
        btn_baja.bind(on_press=self.pedir_baja)
        raiz.add_widget(btn_baja)

        raiz.add_widget(Label(text="— Consultar notas de un alumno —", font_size=13,
                              size_hint=(1, 0.04), color=(0.7, 0.9, 1, 1)))
        self.f_buscar = TextInput(hint_text="Matrícula a consultar", multiline=False, size_hint=(1, 0.07))
        raiz.add_widget(self.f_buscar)
        btn_buscar = Button(text="Consultar", size_hint=(1, 0.07),
                            font_size=15, background_color=COLOR_PRIMARIO)
        btn_buscar.bind(on_press=self.consultar)
        raiz.add_widget(btn_buscar)

        scroll = ScrollView(size_hint=(1, 0.22))
        self.panel = Label(text="", font_size=13, size_hint_y=None,
                           halign="left", valign="top")
        self.panel.bind(texture_size=lambda i, s: setattr(self.panel, "height", s[1]))
        self.panel.bind(width=lambda i, w: setattr(self.panel, "text_size", (w, None)))
        scroll.add_widget(self.panel)
        raiz.add_widget(scroll)

        btn_volver = Button(text="↩ Regresar", size_hint=(1, 0.07), font_size=15,
                            background_color=COLOR_NEUTRO)
        btn_volver.bind(on_press=lambda x: setattr(self.manager, "current", "menu_registro"))
        raiz.add_widget(btn_volver)
        self.add_widget(raiz)

    def guardar(self, inst):
        mat  = self.f_mat.text.strip()
        sec  = self.f_sec.text.strip()
        parc = self.f_parc.text.strip()
        fin  = self.f_fin.text.strip()
        com  = self.f_com.text.strip()
        if not all([mat, sec, parc, fin]):
            notificar("Campos requeridos", "Matrícula, ID de sección, parcial y final son obligatorios.")
            return
        try:
            sec_i  = int(sec)
            parc_f = float(parc)
            fin_f  = float(fin)
        except ValueError:
            notificar("Formato inválido", "ID entero; notas numéricas.")
            return
        if not (0 <= parc_f <= 100) or not (0 <= fin_f <= 100):
            notificar("Rango inválido", "Las notas deben estar entre 0 y 100.")
            return
        with abrir_conexion() as cn:
            al     = cn.execute("SELECT id_alumno FROM alumno WHERE matricula=?", (mat,)).fetchone()
            sec_ok = cn.execute("SELECT 1 FROM seccion WHERE id_seccion=?", (sec_i,)).fetchone()
        if not al:
            notificar("No encontrado", f"No existe el alumno con matrícula '{mat}'.")
            return
        if not sec_ok:
            notificar("No encontrado", f"No existe la sección con ID {sec_i}.")
            return
        try:
            with abrir_conexion() as cn:
                cn.execute("""
                    INSERT INTO evaluacion (nota_parcial, nota_final, comentario, id_alumno, id_seccion)
                    VALUES (?,?,?,?,?)
                    ON CONFLICT(id_alumno, id_seccion) DO UPDATE SET
                        nota_parcial=excluded.nota_parcial,
                        nota_final=excluded.nota_final,
                        comentario=excluded.comentario
                """, (parc_f, fin_f, com or None, al["id_alumno"], sec_i))
            for c in [self.f_mat, self.f_sec, self.f_parc, self.f_fin, self.f_com]:
                c.text = ""
            notificar("Guardado", "Nota registrada correctamente.")
        except Exception as e:
            notificar("Error", str(e))

    def pedir_baja(self, inst):
        mat = self.f_baja_mat.text.strip()
        sec = self.f_baja_sec.text.strip()
        if not mat or not sec:
            notificar("Campos vacíos", "Ingresa matrícula e ID de sección.")
            return
        try:
            sec_i = int(sec)
        except ValueError:
            notificar("Formato inválido", "El ID de sección debe ser entero.")
            return
        with abrir_conexion() as cn:
            reg = cn.execute("""
                SELECT a.nombre, a.paterno, asig.titulo AS materia
                FROM evaluacion ev
                JOIN alumno     a    ON ev.id_alumno  = a.id_alumno
                JOIN seccion    s    ON ev.id_seccion = s.id_seccion
                JOIN asignatura asig ON s.id_asignatura = asig.id_asignatura
                WHERE a.matricula=? AND ev.id_seccion=?
            """, (mat, sec_i)).fetchone()
        if not reg:
            notificar("No encontrado",
                      f"No existe nota para matrícula '{mat}' en sección {sec}.")
            return
        pedir_confirmacion(
            "Confirmar eliminación",
            f"¿Eliminar la nota de\n{reg['nombre']} {reg['paterno']}\nen {reg['materia']}?",
            lambda: self.eliminar(mat, sec_i)
        )

    def eliminar(self, mat, sec_i):
        try:
            with abrir_conexion() as cn:
                cn.execute("""
                    DELETE FROM evaluacion
                    WHERE id_alumno = (SELECT id_alumno FROM alumno WHERE matricula=?)
                      AND id_seccion = ?
                """, (mat, sec_i))
            self.f_baja_mat.text = ""
            self.f_baja_sec.text = ""
            notificar("Eliminado", "Nota eliminada correctamente.")
        except Exception as e:
            notificar("Error", str(e))

    def consultar(self, inst):
        mat = self.f_buscar.text.strip()
        if not mat:
            notificar("Campo vacío", "Ingresa una matrícula.")
            return
        try:
            with abrir_conexion() as cn:
                al = cn.execute(
                    "SELECT nombre, paterno FROM alumno WHERE matricula=?", (mat,)
                ).fetchone()
            if not al:
                self.panel.text = f"No existe el alumno con matrícula '{mat}'."
                return
            with abrir_conexion() as cn:
                rows = cn.execute("""
                    SELECT asig.titulo AS materia, c.denominacion AS ciclo,
                           ev.nota_parcial, ev.nota_final, ev.comentario
                    FROM evaluacion ev
                    JOIN seccion    s    ON ev.id_seccion   = s.id_seccion
                    JOIN asignatura asig ON s.id_asignatura = asig.id_asignatura
                    JOIN ciclo      c    ON s.id_ciclo      = c.id_ciclo
                    JOIN alumno     a    ON ev.id_alumno    = a.id_alumno
                    WHERE a.matricula = ?
                    ORDER BY c.denominacion, asig.titulo
                """, (mat,)).fetchall()
            if not rows:
                self.panel.text = f"{al['nombre']} {al['paterno']}\nSin notas registradas."
                return
            txt = f"Notas de {al['nombre']} {al['paterno']}:\n\n"
            for r in rows:
                p  = f"{r['nota_parcial']:.1f}" if r['nota_parcial'] is not None else "--"
                f_ = f"{r['nota_final']:.1f}"   if r['nota_final']   is not None else "--"
                txt += f"{r['materia']}\n"
                txt += f"Ciclo: {r['ciclo']}  Parcial: {p}  Final: {f_}\n"
                if r['comentario']:
                    txt += f"Comentario: {r['comentario']}\n"
                txt += "\n"
            self.panel.text = txt
        except Exception as e:
            self.panel.text = f"Error: {e}"



# ══════════════════════════════════════════════════════════════════
#  PANTALLAS DE CONSULTA (INTEGRANDO TU NUEVA FUNCIÓN)
# ══════════════════════════════════════════════════════════════════
class PantallaConsultaAlumnos(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=20, spacing=11)
        raiz.add_widget(Label(text="Directorio de Alumnos", font_size=24,
                              size_hint=(1, 0.14), color=(0.85, 0.95, 1, 1)))

        # Cambiado a COLOR_PRIMARIO
        btn_ver = Button(text="Cargar directorio", size_hint=(1, 0.12),
                         font_size=15, background_color=COLOR_PRIMARIO)
        btn_ver.bind(on_press=self.ver_todos)
        raiz.add_widget(btn_ver)

        self.panel = Label(
            text="Presiona el botón para cargar el directorio.",
            font_size=13, size_hint=(1, 0.60),
            halign="left", valign="top"
        )
        self.panel.bind(size=self.panel.setter("text_size"))
        raiz.add_widget(self.panel)

        # Cambiado a COLOR_NEUTRO y retorno a menu_consulta
        btn_atras = Button(text="↩ Volver", size_hint=(1, 0.12),
                           font_size=15, background_color=COLOR_NEUTRO)
        btn_atras.bind(on_press=lambda x: setattr(self.manager, "current", "menu_consulta"))
        raiz.add_widget(btn_atras)
        self.add_widget(raiz)

    def ver_todos(self, inst):
        try:
            with abrir_conexion() as cn:
                rows = cn.execute("""
                    SELECT a.matricula, a.nombre, a.paterno, a.nivel, p.titulo AS programa
                    FROM alumno a
                    JOIN programa p ON a.id_programa = p.id_programa
                    ORDER BY a.paterno
                """).fetchall()
            if not rows:
                self.panel.text = "Sin alumnos registrados en el sistema."
                return
            txt = "Alumnos inscritos:\n\n"
            for i, r in enumerate(rows, 1):
                txt += f"{i}. {r['nombre']} {r['paterno']}  [{r['matricula']}]\n"
                txt += f"   Nivel {r['nivel']}  —  {r['programa']}\n\n"
            self.panel.text = txt
        except Exception as e:
            self.panel.text = f"Error: {e}"

    def on_enter(self):
        self.ver_todos(None)


class PantallaConsultaDocentes(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=20, spacing=11)
        raiz.add_widget(Label(text="Directorio de Docentes", font_size=24,
                              size_hint=(1, 0.14), color=(0.85, 0.95, 1, 1)))

        # Cambiado a COLOR_PRIMARIO
        btn_ver = Button(text="Cargar directorio", size_hint=(1, 0.12),
                         font_size=15, background_color=COLOR_PRIMARIO)
        btn_ver.bind(on_press=self.ver_todos)
        raiz.add_widget(btn_ver)

        self.panel = Label(
            text="Presiona el botón para cargar el directorio.",
            font_size=13, size_hint=(1, 0.60),
            halign="left", valign="top"
        )
        self.panel.bind(size=self.panel.setter("text_size"))
        raiz.add_widget(self.panel)

        # Cambiado a COLOR_NEUTRO y retorno a menu_consulta
        btn_atras = Button(text="↩ Volver", size_hint=(1, 0.12),
                           font_size=15, background_color=COLOR_NEUTRO)
        btn_atras.bind(on_press=lambda x: setattr(self.manager, "current", "menu_consulta"))
        raiz.add_widget(btn_atras)
        self.add_widget(raiz)

    def ver_todos(self, inst):
        try:
            with abrir_conexion() as cn:
                rows = cn.execute("SELECT * FROM docente ORDER BY paterno").fetchall()
            if not rows:
                self.panel.text = "Sin docentes registrados en el sistema."
                return
            txt = "Planta docente:\n\n"
            for i, r in enumerate(rows, 1):
                txt += f"{i}. {r['nombre']} {r['paterno']}\n"
                txt += f"   {r['area'] or 'Área no asignada'}\n\n"
            self.panel.text = txt
        except Exception as e:
            self.panel.text = f"Error: {e}"

    def on_enter(self):
        self.ver_todos(None)


class PantallaConsultaSecciones(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=20, spacing=11)
        raiz.add_widget(Label(text="Horarios y Secciones", font_size=24,
                              size_hint=(1, 0.14), color=(0.85, 0.95, 1, 1)))

        # Cambiado a COLOR_PRIMARIO
        btn_ver = Button(text="Ver horarios", size_hint=(1, 0.12),
                         font_size=15, background_color=COLOR_PRIMARIO)
        btn_ver.bind(on_press=self.ver_todos)
        raiz.add_widget(btn_ver)

        self.panel = Label(
            text="Presiona el botón para ver los horarios.",
            font_size=13, size_hint=(1, 0.60),
            halign="left", valign="top"
        )
        self.panel.bind(size=self.panel.setter("text_size"))
        raiz.add_widget(self.panel)

        # Cambiado a COLOR_NEUTRO y retorno a menu_consulta
        btn_atras = Button(text="↩ Volver", size_hint=(1, 0.12),
                           font_size=15, background_color=COLOR_NEUTRO)
        btn_atras.bind(on_press=lambda x: setattr(self.manager, "current", "menu_consulta"))
        raiz.add_widget(btn_atras)
        self.add_widget(raiz)

    def ver_todos(self, inst):
        try:
            with abrir_conexion() as cn:
                rows = cn.execute("""
                    SELECT asig.titulo AS materia,
                           d.nombre || ' ' || d.paterno AS docente,
                           e.referencia AS espacio,
                           c.denominacion AS ciclo,
                           s.turno
                    FROM seccion s
                    JOIN asignatura asig ON s.id_asignatura = asig.id_asignatura
                    JOIN docente    d    ON s.id_docente    = d.id_docente
                    JOIN espacio    e    ON s.id_espacio    = e.id_espacio
                    JOIN ciclo      c    ON s.id_ciclo      = c.id_ciclo
                    ORDER BY c.denominacion, asig.titulo
                """).fetchall()
            if not rows:
                self.panel.text = "Sin secciones registradas en el sistema."
                return
            txt = "Secciones activas:\n\n"
            for i, r in enumerate(rows, 1):
                txt += f"{i}. {r['materia']}\n"
                txt += f"   Docente: {r['docente']}\n"
                txt += f"   {r['turno']}  |  Espacio: {r['espacio']}\n"
                txt += f"   Ciclo: {r['ciclo']}\n\n"
            self.panel.text = txt
        except Exception as e:
            self.panel.text = f"Error: {e}"

    def on_enter(self):
        self.ver_todos(None)


class PantallaConsultaEvaluaciones(Screen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        raiz = BoxLayout(orientation="vertical", padding=20, spacing=11)
        raiz.add_widget(Label(text="Calificaciones", font_size=24,
                              size_hint=(1, 0.14), color=(0.85, 0.95, 1, 1)))

        self.f_buscar = TextInput(
            hint_text="Ingresa tu matrícula",
            multiline=False, size_hint=(1, 0.10)
        )
        raiz.add_widget(self.f_buscar)

        # Cambiado a COLOR_PRIMARIO
        btn_buscar = Button(text="Ver mis calificaciones", size_hint=(1, 0.12),
                            font_size=15, background_color=COLOR_PRIMARIO)
        btn_buscar.bind(on_press=self.consultar)
        raiz.add_widget(btn_buscar)

        self.panel = Label(
            text="Ingresa tu matrícula y presiona el botón.",
            font_size=13, size_hint=(1, 0.50),
            halign="left", valign="top"
        )
        self.panel.bind(size=self.panel.setter("text_size"))
        raiz.add_widget(self.panel)

        # Cambiado a COLOR_NEUTRO y retorno a menu_consulta
        btn_atras = Button(text="↩ Volver", size_hint=(1, 0.12),
                           font_size=15, background_color=COLOR_NEUTRO)
        btn_atras.bind(on_press=lambda x: setattr(self.manager, "current", "menu_consulta"))
        raiz.add_widget(btn_atras)
        self.add_widget(raiz)

    def consultar(self, inst):
        mat = self.f_buscar.text.strip()
        if not mat:
            notificar("Campo vacío", "Ingresa tu matrícula.")
            return
        try:
            with abrir_conexion() as cn:
                alumno = cn.execute(
                    "SELECT nombre, paterno FROM alumno WHERE matricula = ?", (mat,)
                ).fetchone()

            if not alumno:
                self.panel.text = f"No se encontró ningún alumno con matrícula '{mat}'."
                return

            with abrir_conexion() as cn:
                rows = cn.execute("""
                    SELECT asig.titulo AS materia, c.denominacion AS ciclo,
                           ev.nota_parcial, ev.nota_final, ev.comentario
                    FROM evaluacion ev
                    JOIN seccion    s    ON ev.id_seccion   = s.id_seccion
                    JOIN asignatura asig ON s.id_asignatura = asig.id_asignatura
                    JOIN ciclo      c    ON s.id_ciclo      = c.id_ciclo
                    JOIN alumno     a    ON ev.id_alumno    = a.id_alumno
                    WHERE a.matricula = ?
                    ORDER BY c.denominacion, asig.titulo
                """, (mat,)).fetchall()

            nombre_completo = f"{alumno['nombre']} {alumno['paterno']}"

            if not rows:
                self.panel.text = (f"Alumno: {nombre_completo}\n\n"
                                   "Aún no tiene calificaciones registradas.")
                return

            txt = f"Alumno: {nombre_completo}\nMatrícula: {mat}\n\n"
            for r in rows:
                p  = f"{r['nota_parcial']:.1f}" if r['nota_parcial'] is not None else "--"
                f_ = f"{r['nota_final']:.1f}"   if r['nota_final']   is not None else "--"
                txt += f"{r['materia']}\n"
                txt += f"Ciclo: {r['ciclo']}\n"
                txt += f"Parcial: {p}   Final: {f_}\n"
                if r['comentario']:
                    txt += f"Nota: {r['comentario']}\n"
                txt += "\n"
            self.panel.text = txt

        except Exception as e:
            self.panel.text = f"Error al consultar: {e}"


# ══════════════════════════════════════════════════════════════════
#  CLASE PRINCIPAL Y ARRANQUE DE KIVY
# ══════════════════════════════════════════════════════════════════
class AppAcademico(App):
    title = "Sistema Académico — Gestión Universitaria"

    def build(self):
        # Crear base de datos y tablas si no existen
        crear_tablas()

        # Configurar gestor de pantallas
        gestor = ScreenManager()
        gestor.add_widget(PantallaInicio(name="inicio"))
        
        # Pantallas de Menú
        gestor.add_widget(PantallaMenuRegistro(name="menu_registro"))
        gestor.add_widget(PantallaMenuConsulta(name="menu_consulta"))
        
        # Pantallas de Registro (administración)
        gestor.add_widget(PantallaProgramas(name="programas"))
        gestor.add_widget(PantallaDocentes(name="docentes"))
        gestor.add_widget(PantallaAlumnos(name="alumnos"))
        gestor.add_widget(PantallaAsignaturas(name="asignaturas"))
        gestor.add_widget(PantallaEspacios(name="espacios"))
        gestor.add_widget(PantallaCiclos(name="ciclos"))
        gestor.add_widget(PantallaSecciones(name="secciones"))
        gestor.add_widget(PantallaInscripciones(name="inscripciones"))
        gestor.add_widget(PantallaEvaluaciones(name="evaluaciones"))

        # Pantallas de Consulta
        gestor.add_widget(PantallaConsultaAlumnos(name="consulta_alumnos"))
        gestor.add_widget(PantallaConsultaDocentes(name="consulta_docentes"))
        gestor.add_widget(PantallaConsultaSecciones(name="consulta_secciones"))
        gestor.add_widget(PantallaConsultaEvaluaciones(name="consulta_evaluaciones"))

        return gestor

if __name__ == "__main__":
    AppAcademico().run()
