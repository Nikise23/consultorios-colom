# --- ACCESO SQLITE USUARIOS ---
import sqlite3
from flask import Flask, request, jsonify, render_template, redirect, url_for, session, make_response, send_file
import json
import os
import csv
import io
import shutil
import time
from functools import wraps
from datetime import datetime, date, timezone, timedelta
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_insegura_dev")

# Configurar zona horaria para Argentina (UTC-3)
import pytz
timezone_ar = pytz.timezone('America/Argentina/Buenos_Aires')

# Función para obtener conexión a la base de datos con timeout
def get_db_connection():
    """Obtener conexión a la base de datos con timeout y configuración optimizada"""
    import time
    import random
    
    max_retries = 5
    base_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            conn = sqlite3.connect("data/consultorio.db", timeout=30.0)
            conn.execute("PRAGMA journal_mode=WAL")  # Modo WAL para mejor concurrencia
            conn.execute("PRAGMA synchronous=NORMAL")  # Balance entre seguridad y velocidad
            conn.execute("PRAGMA cache_size=10000")  # Cache más grande
            conn.execute("PRAGMA temp_store=MEMORY")  # Tablas temporales en memoria
            conn.execute("PRAGMA busy_timeout=30000")  # 30 segundos de timeout para operaciones
            return conn
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < max_retries - 1:
                # Esperar con backoff exponencial + jitter
                delay = base_delay * (2 ** attempt) + random.uniform(0, 0.1)
                print(f"DEBUG - Base de datos bloqueada, reintentando en {delay:.2f}s (intento {attempt + 1}/{max_retries})")
                time.sleep(delay)
                continue
            else:
                print(f"ERROR - No se pudo conectar a la base de datos después de {max_retries} intentos: {e}")
                raise
        except Exception as e:
            print(f"ERROR - Error inesperado al conectar a la base de datos: {e}")
            raise

# --- API error handlers: devolver JSON en rutas /api/* ---
@app.errorhandler(401)
def handle_401(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "No autenticado"}), 401
    return e

@app.errorhandler(403)
def handle_403(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "No autorizado"}), 403
    return e

@app.errorhandler(404)
def handle_404(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "No encontrado"}), 404
    return e

@app.errorhandler(500)
def handle_500(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Error interno del servidor"}), 500
    return e

@app.errorhandler(400)
def handle_400(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Solicitud inválida"}), 400
    return e

@app.errorhandler(405)
def handle_405(e):
    if request.path.startswith('/api/'):
        return jsonify({"error": "Método no permitido"}), 405
    return e

# --- ACCESO SQLITE USUARIOS ---
def cargar_usuarios_db():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM usuarios")
    columnas = [desc[0] for desc in c.description]
    usuarios = [dict(zip(columnas, row)) for row in c.fetchall()]
    conn.close()
    return usuarios

# Rutas de archivo usando el disco persistente
# Configuración de base de datos
DATABASE_PATH = "data/consultorio.db"

# # (OPCIONAL) Copiar archivos antiguos si todavía existen en la raíz
# def mover_a_persistencia(nombre_archivo):
#     origen = nombre_archivo
#     destino = f"/data/{nombre_archivo}"
    
#     if os.path.exists(origen) and not os.path.exists(destino):
#         try:
#             shutil.copy(origen, destino)
#             print(f"✅ Archivo '{nombre_archivo}' copiado a /data")
#         except Exception as e:
#             print(f"❌ Error al copiar '{nombre_archivo}':", e)
#     else:
#         print(f"🔁 '{nombre_archivo}' ya existe en /data o no se encontró en el origen.")

# archivos_para_mover = [
#     "historias_clinicas.json",
#     "usuarios.json",
#     "pacientes.json",
#     "turnos.json",
#     "agenda.json",
#     "pagos.json"
# ]

# for archivo in archivos_para_mover:
#     mover_a_persistencia(archivo)


# ===================== Funciones auxiliares ======================

def cargar_json(path):
    """Carga datos desde SQLite según el archivo lógico solicitado.

    Mantiene las estructuras que el código espera cuando antes leía JSON.
    """
    db_path = "data/consultorio.db"
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    try:
        if path == USUARIOS_FILE:
            c.execute("SELECT usuario, contrasena, rol FROM usuarios")
            return [dict(row) for row in c.fetchall()]

        if path == PACIENTES_FILE:
            c.execute(
                """
                SELECT dni, nombre, apellido, fecha_nacimiento, obra_social,
                       numero_obra_social, celular
                FROM pacientes
                """
            )
            rows = [dict(row) for row in c.fetchall()]
            # Calcular edad desde fecha_nacimiento para mantener compatibilidad
            for r in rows:
                if r.get("fecha_nacimiento"):
                    r["edad"] = calcular_edad(r["fecha_nacimiento"]) or 0
                else:
                    r["edad"] = 0
            return rows

        if path == TURNOS_FILE:
            c.execute(
                """
                SELECT id, medico, hora_turno as hora, fecha_turno as fecha, dni_paciente, estado,
                       tipo_consulta, costo, pagado, observaciones
                FROM turnos
                ORDER BY fecha_turno DESC, hora_turno ASC
                """
            )
            rows = [dict(row) for row in c.fetchall()]
            # Mantener compatibilidad con el código existente
            for r in rows:
                r["pago_registrado"] = bool(r.get("pagado", 0))
                r["monto_pagado"] = float(r.get("costo") or 0)
                r["dni_paciente"] = str(r.get("dni_paciente") or "")
            return rows

        if path == AGENDA_FILE:
            # Reconstruir estructura { medico: { DIA: [horas...] } }
            c.execute("SELECT medico, dia_semana as dia, horario as hora FROM agenda")
            agenda = {}
            for medico, dia, hora in c.fetchall():
                agenda.setdefault(medico, {}).setdefault(dia, []).append(hora)
            # Ordenar horas para estabilidad
            for medico in list(agenda.keys()):
                # normalizar claves de días a minúsculas para el frontend
                normalizado = {}
                for dia, horas in agenda[medico].items():
                    normalizado[dia.lower()] = sorted(horas)
                agenda[medico] = normalizado
            return agenda

        if path == PAGOS_FILE:
            c.execute(
                """
                SELECT id, dni_paciente, monto, fecha_pago as fecha, metodo_pago, obra_social, observaciones, fecha_creacion
                FROM pagos
                ORDER BY id
                """
            )
            rows = [dict(row) for row in c.fetchall()]
            # Agregar campos faltantes para compatibilidad
            for r in rows:
                r["nombre_paciente"] = ""  # Se puede obtener del JOIN con pacientes si es necesario
                r["hora"] = ""  # No disponible en el esquema actual
                r["fecha_registro"] = r.get("fecha_creacion", "")
                r["tipo_pago"] = r.get("metodo_pago", "")
                r["monto"] = float(r.get("monto") or 0)
                r["dni_paciente"] = str(r.get("dni_paciente") or "")
            return rows

        if path == DATA_FILE:
            # Historias clínicas
            c.execute(
                """
                SELECT dni, consulta_medica, medico, fecha_consulta
                FROM historias_clinicas
                """
            )
            rows = [dict(row) for row in c.fetchall()]
            for r in rows:
                r["dni"] = str(r.get("dni") or "")
            return rows

        # Si no coincide ningún archivo lógico, devolver lista vacía
        return []
    finally:
        conn.close()


def guardar_json(path, data):
    """Persiste datos en SQLite reemplazando el contenido de la tabla asociada.

    El resto del código sigue llamando a esta función como si escribiera JSON.
    """
    db_path = "data/consultorio.db"
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    try:
        if path == USUARIOS_FILE:
            with conn:
                c.execute("DELETE FROM usuarios")
                for u in (data or []):
                    c.execute(
                        "INSERT INTO usuarios (usuario, contrasena, rol) VALUES (?, ?, ?)",
                        (u.get("usuario", "").strip(), u.get("contrasena", ""), u.get("rol", "")),
                    )
            return

        if path == PACIENTES_FILE:
            with conn:
                c.execute("DELETE FROM pacientes")
                for p in (data or []):
                    c.execute(
                        """
                        INSERT OR REPLACE INTO pacientes
                        (dni, nombre, apellido, fecha_nacimiento, obra_social, numero_obra_social, celular)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(p.get("dni", "")).strip(),
                            p.get("nombre", ""),
                            p.get("apellido", ""),
                            p.get("fecha_nacimiento", ""),
                            p.get("obra_social", ""),
                            str(p.get("numero_obra_social", "")),
                            str(p.get("celular", "")),
                        ),
                    )
            return

        if path == TURNOS_FILE:
            with conn:
                c.execute("DELETE FROM turnos")
                for t in (data or []):
                    c.execute(
                        """
                        INSERT INTO turnos
                        (medico, hora_turno, fecha_turno, dni_paciente, estado, tipo_consulta, costo, pagado, observaciones)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            t.get("medico", ""),
                            t.get("hora", ""),
                            t.get("fecha", ""),
                            str(t.get("dni_paciente", "")),
                            t.get("estado", ""),
                            t.get("tipo_consulta", ""),
                            float(t.get("costo", 0) or 0),
                            int(t.get("pagado", 0) or 0),
                            t.get("observaciones", ""),
                        ),
                    )
            return

        if path == AGENDA_FILE:
            # data esperado: { medico: { DIA: [horas...] } }
            with conn:
                c.execute("DELETE FROM agenda")
                if isinstance(data, dict):
                    for medico, dias in data.items():
                        if not isinstance(dias, dict):
                            continue
                        for dia, horas in dias.items():
                            if not isinstance(horas, list):
                                continue
                            for hora in horas:
                                c.execute(
                                    "INSERT OR IGNORE INTO agenda (medico, dia_semana, horario) VALUES (?, ?, ?)",
                                    (medico, dia, hora),
                                )
            return

        if path == PAGOS_FILE:
            with conn:
                c.execute("DELETE FROM pagos")
                for p in (data or []):
                    c.execute(
                        """
                        INSERT INTO pagos (id, dni_paciente, monto, fecha_pago, metodo_pago, obra_social, observaciones, fecha_creacion)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            int(p.get("id")) if p.get("id") is not None else None,
                            str(p.get("dni_paciente", "")),
                            float(p.get("monto", 0) or 0),
                            p.get("fecha", ""),
                            p.get("metodo_pago", ""),
                            str(p.get("obra_social", "")),
                            p.get("observaciones", ""),
                            p.get("fecha_registro", ""),
                        ),
                    )
            return

        if path == DATA_FILE:
            # Historias clínicas
            with conn:
                c.execute("DELETE FROM historias_clinicas")
                for h in (data or []):
                    c.execute(
                        "INSERT INTO historias_clinicas (dni, consulta_medica, medico, fecha_consulta) VALUES (?, ?, ?, ?)",
                        (
                            str(h.get("dni", "")),
                            h.get("consulta_medica", ""),
                            h.get("medico", ""),
                            h.get("fecha_consulta", ""),
                        ),
                    )
            return
    finally:
        conn.close()


def calcular_edad(fecha_nacimiento):
    """Calcula la edad a partir de la fecha de nacimiento"""
    try:
        fecha_nac = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
        hoy = date.today()
        edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
        return edad
    except:
        return None

def validar_historia(data):
    campos_obligatorios = ["dni", "consulta_medica", "medico"]
    for campo in campos_obligatorios:
        if not data.get(campo) or not str(data[campo]).strip():
            return False, f"El campo '{campo}' es obligatorio."


    if not data["dni"].isdigit() or len(data["dni"]) not in [7, 8]:
        return False, "DNI inválido."


    for campo in ["fecha_consulta"]:
        fecha = data.get(campo)
        if fecha:
            try:
                f = datetime.strptime(fecha, "%Y-%m-%d")
                # Convertir a timezone-aware para comparar
                f = f.replace(tzinfo=timezone_ar)
                ahora = datetime.now(timezone_ar)
                if f > ahora:
                    return False, f"La fecha '{campo}' no puede ser futura."
            except ValueError:
                return False, f"Formato de fecha inválido en '{campo}'."


    return True, ""


def login_requerido(f):
    @wraps(f)
    def decorated(*args, **kwargs):
            # Para endpoints API, devolver JSON 401 en lugar de redirigir HTML
        if "usuario" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "No autenticado"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def rol_requerido(rol_permitido):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get("rol") != rol_permitido:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "No autorizado"}), 403
                return redirect(url_for("inicio"))
            return f(*args, **kwargs)
        return decorated
    return wrapper


def rol_permitido(varios_roles):
    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if session.get("rol") not in varios_roles:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "No autorizado"}), 403
                return redirect(url_for("inicio"))
            return f(*args, **kwargs)
        return decorated
    return wrapper


# ========================== RUTAS GENERALES ============================

@app.route('/descargar/<archivo>')
@login_requerido
@rol_requerido("administrador")
def descargar_archivo(archivo):
    ruta = f"/data/{archivo}"
    if os.path.exists(ruta):
        return send_file(ruta, as_attachment=True)
    else:
        return f"Archivo '{archivo}' no encontrado", 404


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        usuario = request.form.get("usuario")
        contrasena = request.form.get("contrasena")
        usuarios = cargar_usuarios_db()
        for u in usuarios:
            if u["usuario"] == usuario:
                # Verificar que el hash no esté vacío
                hash_contraseña = u.get("contrasena", "")
                if not hash_contraseña or not hash_contraseña.strip():
                    print(f"ERROR - Usuario {usuario} tiene hash de contraseña vacío")
                    continue
                try:
                    if check_password_hash(hash_contraseña, contrasena):
                        session["usuario"] = usuario
                        session["rol"] = u.get("rol", "")
                        # Redirigir según el rol
                        if u.get("rol") == "secretaria":
                            return redirect(url_for("vista_secretaria"))
                        elif u.get("rol") == "administrador":
                            return redirect(url_for("vista_administrador"))
                        else:
                            return redirect(url_for("inicio"))
                except ValueError as e:
                    print(f"ERROR - Hash inválido para usuario {usuario}: {e}")
                    continue
        return render_template("login.html", error="Usuario o contraseña incorrectos")


    return render_template("login.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    """Endpoint de login para API que devuelve JSON en lugar de redirigir"""
    data = request.json
    if not data or not data.get("usuario") or not data.get("contrasena"):
        return jsonify({"error": "Usuario y contraseña requeridos"}), 400
    
    usuarios = cargar_usuarios_db()
    for u in usuarios:
        if u["usuario"] == data["usuario"] and check_password_hash(u["contrasena"], data["contrasena"]):
            session["usuario"] = data["usuario"]
            session["rol"] = u.get("rol", "")
            return jsonify({
                "mensaje": "Login exitoso",
                "usuario": data["usuario"],
                "rol": u.get("rol", "")
            }), 200
    
    return jsonify({"error": "Usuario o contraseña incorrectos"}), 401


@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.pop("usuario", None)
    session.pop("rol", None)
    if request.method == "POST":
        return jsonify({"message": "Sesión cerrada correctamente"}), 200
    return redirect(url_for("login"))


@app.route("/")
@login_requerido
def inicio():
    return render_template("index.html")


@app.route("/api/session-info")
@login_requerido
def session_info():
    return jsonify({
        "usuario": session.get("usuario"),
        "rol": session.get("rol")
    })


# ========================== MÉDICO ============================


@app.route("/historias", methods=["GET"])
@login_requerido
@rol_requerido("medico")
def ver_historia_clinica():
    dni = request.args.get("dni", "").strip()
    if not dni:
        return "DNI no especificado", 400
    return render_template("historia_clinica.html", dni=dni)


@app.route("/api/historias", methods=["GET"])
@login_requerido
@rol_requerido("medico")
def obtener_todas_las_historias():
    historias = cargar_json(DATA_FILE)
    return jsonify(historias)


@app.route("/api/usuarios", methods=["GET"])
@login_requerido
def obtener_usuarios():
    """Obtener todos los usuarios del sistema"""
    try:
        usuarios = cargar_usuarios_db()
        return jsonify(usuarios)
    except Exception as e:
        return jsonify({"error": f"Error al cargar usuarios: {str(e)}"}), 500


@app.route("/historias", methods=["POST"])
@login_requerido
@rol_requerido("medico")
def crear_historia():
    historias = cargar_json(DATA_FILE)
    nueva = request.get_json(silent=True)
    if not isinstance(nueva, dict):
        return jsonify({"error": "Cuerpo inválido; enviar JSON"}), 400


    valido, mensaje = validar_historia(nueva)
    if not valido:
        return jsonify({"error": mensaje}), 400


    # Agregar ID único para la consulta
    nueva["id"] = len(historias) + 1
    nueva["fecha_creacion"] = datetime.now(timezone_ar).isoformat()


    historias.append(nueva)
    guardar_json(DATA_FILE, historias)
    # Crear ficha mínima si no existe el paciente (para que secretaria complete luego)
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        dni = str(nueva.get("dni", "")).strip()
        if dni:
            cur.execute("SELECT 1 FROM pacientes WHERE dni=?", (dni,))
            if not cur.fetchone():
                cur.execute(
                    """
                    INSERT OR IGNORE INTO pacientes (dni, nombre, apellido, fecha_nacimiento, obra_social, numero_obra_social, celular)
                    VALUES (?, '', '', '', '', '', '')
                    """,
                    (dni,),
                )
                conn.commit()
    except Exception:
        pass
    finally:
        try:
            conn.close()
        except Exception:
            pass
    return jsonify({"mensaje": "Consulta registrada correctamente"}), 201


@app.route("/historias/<dni>", methods=["GET", "PUT", "DELETE"])
@login_requerido
@rol_requerido("medico")
def manejar_historia(dni):
    historias = cargar_json(DATA_FILE)


    if request.method == "GET":
        for h in historias:
            if h["dni"] == dni:
                return jsonify(h)
        return jsonify({"error": "Historia no encontrada"}), 404


    if request.method == "PUT":
        datos = request.json
        valido, mensaje = validar_historia(datos)
        if not valido:
            return jsonify({"error": mensaje}), 400


        for h in historias:
            if h["dni"] == dni:
                h.update(datos)
                guardar_json(DATA_FILE, historias)
                return jsonify({"mensaje": "Historia modificada"})
        return jsonify({"error": "Historia no encontrada"}), 404


    if request.method == "DELETE":
        nuevas = [h for h in historias if h["dni"] != dni]
        if len(nuevas) == len(historias):
            return jsonify({"error": "Historia no encontrada"}), 404
        guardar_json(DATA_FILE, nuevas)
        return jsonify({"mensaje": "Historia eliminada"})


# ========================== SECRETARIA ============================


@app.route("/pacientes")
@login_requerido
@rol_requerido("secretaria")
def vista_pacientes():
    return render_template("pacientes.html")


@app.route("/api/pacientes", methods=["GET"])
@login_requerido
@rol_permitido(["secretaria", "medico"])
def obtener_pacientes():
    pacientes = cargar_json(PACIENTES_FILE)
    pacientes.sort(key=lambda p: p.get("apellido", "").lower())
    return jsonify(pacientes)


@app.route("/api/pacientes", methods=["POST"])
@login_requerido
@rol_requerido("secretaria")
def registrar_paciente():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Cuerpo inválido; enviar JSON"}), 400
    campos = ["nombre", "apellido", "dni", "obra_social", "numero_obra_social", "celular", "fecha_nacimiento"]
    for campo in campos:
        if not data.get(campo) or not str(data[campo]).strip():
            return jsonify({"error": f"El campo '{campo}' es obligatorio"}), 400
    # Validar DNI: solo números y máximo 8 dígitos (acepta 7 u 8)
    dni_str = str(data.get("dni", "")).strip()
    if not dni_str.isdigit() or len(dni_str) > 8 or len(dni_str) < 7:
        return jsonify({"error": "DNI inválido (solo números, 7 u 8 dígitos)"}), 400
    
     # Calcular edad automáticamente
    if data.get("fecha_nacimiento"):
        edad = calcular_edad(data["fecha_nacimiento"])
        data["edad"] = edad

    pacientes = cargar_json(PACIENTES_FILE)
    if any(p["dni"] == data["dni"] for p in pacientes):
        return jsonify({"error": "Ya existe un paciente con ese DNI"}), 400

    pacientes.append(data)
    guardar_json(PACIENTES_FILE, pacientes)
    return jsonify({"success": True, "mensaje": "Paciente registrado correctamente"})

@app.route("/api/pacientes/<dni>", methods=["PUT"])
@login_requerido
@rol_requerido("secretaria")
def actualizar_paciente(dni):
    data = request.json
    campos = ["nombre", "apellido", "dni", "obra_social", "numero_obra_social", "celular"]
    for campo in campos:
        if not data.get(campo):
            return jsonify({"error": f"El campo '{campo}' es obligatorio"}), 400
    
    # Validar formato del DNI
    if not data["dni"].isdigit() or len(data["dni"]) not in [7, 8]:
        return jsonify({"error": "DNI inválido"}), 400

    # Calcular edad automáticamente si se proporciona fecha de nacimiento
    if data.get("fecha_nacimiento"):
        edad = calcular_edad(data["fecha_nacimiento"])
        data["edad"] = edad

    pacientes = cargar_json(PACIENTES_FILE)

    # Si el DNI cambió, verificar que el nuevo DNI no esté en uso
    if data["dni"] != dni:
        if any(p["dni"] == data["dni"] for p in pacientes):
            return jsonify({"error": "Ya existe un paciente con ese DNI"}), 400
    
    
    for i, paciente in enumerate(pacientes):
        if paciente["dni"] == dni:
            # Actualizar todos los campos incluyendo el DNI
            for campo, valor in data.items():
                pacientes[i][campo] = valor
            
            guardar_json(PACIENTES_FILE, pacientes)
            return jsonify({"mensaje": "Paciente actualizado correctamente"})
    
    return jsonify({"error": "Paciente no encontrado"}), 404

@app.route("/api/pacientes/<dni>", methods=["DELETE"])
@login_requerido
@rol_requerido("secretaria")
def eliminar_paciente(dni):
    pacientes = cargar_json(PACIENTES_FILE)
    
    # Verificar si el paciente tiene turnos asociados
    turnos = cargar_json(TURNOS_FILE)
    turnos_del_paciente = [t for t in turnos if t.get("dni_paciente") == dni]
    
    if turnos_del_paciente:
        return jsonify({
            "error": f"No se puede eliminar el paciente. Tiene {len(turnos_del_paciente)} turno(s) asociado(s). Primero cancele todos sus turnos."
        }), 400
    
    # Buscar y eliminar el paciente
    for i, paciente in enumerate(pacientes):
        if paciente["dni"] == dni:
            pacientes.pop(i)
            guardar_json(PACIENTES_FILE, pacientes)
            
            # También eliminar historias clínicas del paciente
            historias = cargar_json(DATA_FILE)
            historias_filtradas = [h for h in historias if h.get("dni") != dni]
            guardar_json(DATA_FILE, historias_filtradas)
            
            return jsonify({"mensaje": "Paciente eliminado correctamente"})
    
    return jsonify({"error": "Paciente no encontrado"}), 404

# --- Rutas para turnos y agenda ---


@app.route("/api/turnos", methods=["GET"])
@login_requerido
@rol_permitido(["secretaria", "medico"])
def obtener_turnos():
    turnos = cargar_json(TURNOS_FILE)
    pacientes = cargar_json(PACIENTES_FILE)


    for t in turnos:
        paciente = next((p for p in pacientes if p["dni"] == t["dni_paciente"]), None)
        t["paciente"] = paciente
        t["estado"] = t.get("estado", "sin atender")
    return jsonify(turnos)


@app.route("/api/turnos", methods=["POST"])
@login_requerido
@rol_requerido("secretaria")
def asignar_turno():
    data = request.json
    campos = ["medico", "hora", "fecha", "dni_paciente"]
    for campo in campos:
        if not data.get(campo):
            return jsonify({"error": f"El campo '{campo}' es obligatorio"}), 400

    try:
        fecha_dt = datetime.strptime(data["fecha"], "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Formato de fecha inválido (usar YYYY-MM-DD)"}), 400

    dia_semana = fecha_dt.strftime("%A").upper()

    # Mapeo de días de la semana de inglés a español
    dia_es = {
        "MONDAY": "LUNES", "TUESDAY": "MARTES", "WEDNESDAY": "MIERCOLES",
        "THURSDAY": "JUEVES", "FRIDAY": "VIERNES", "SATURDAY": "SABADO", "SUNDAY": "DOMINGO"
    }
    dia_semana_es = dia_es.get(dia_semana, "").upper()

    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()

        # 1. Verificar si el médico tiene horarios configurados para ese día y hora
        c.execute(
            "SELECT * FROM agenda WHERE medico = ? AND dia_semana = ? AND horario = ?",
            (data["medico"], dia_semana_es, data["hora"])
        )
        if not c.fetchone():
            return jsonify({"error": "El médico no tiene horarios configurados para este día y hora"}), 400

        # 2. Verificar si ya existe un turno para ese médico, fecha y hora
        c.execute(
            "SELECT * FROM turnos WHERE medico = ? AND fecha_turno = ? AND hora_turno = ?",
            (data["medico"], data["fecha"], data["hora"])
        )
        if c.fetchone():
            return jsonify({"error": "Ya existe un turno asignado para este médico, fecha y hora"}), 400

        # 3. Verificar si el paciente existe
        c.execute("SELECT * FROM pacientes WHERE dni = ?", (data["dni_paciente"],))
        if not c.fetchone():
            return jsonify({"error": "El paciente con el DNI proporcionado no existe"}), 404

        # 4. Asignar el turno
        c.execute(
            "INSERT INTO turnos (medico, hora_turno, fecha_turno, dni_paciente, estado) VALUES (?, ?, ?, ?, ?)",
            (data["medico"], data["hora"], data["fecha"], data["dni_paciente"], "pendiente")
        )
        conn.commit()

        return jsonify({"mensaje": "Turno asignado correctamente", "turno": data}), 201

    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print(f"ERROR - Base de datos bloqueada al asignar turno: {e}")
            return jsonify({"error": "La base de datos está temporalmente ocupada. Por favor, intente nuevamente en unos segundos."}), 503
        else:
            print(f"ERROR - Error de base de datos al asignar turno: {e}")
            return jsonify({"error": "Error interno al asignar el turno"}), 500
    except sqlite3.Error as e:
        print(f"ERROR - Error de base de datos al asignar turno: {e}")
        return jsonify({"error": "Error interno al asignar el turno"}), 500
    except Exception as e:
        print(f"ERROR - Error inesperado al asignar turno: {e}")
        return jsonify({"error": "Error interno al asignar el turno"}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/turnos/<int:turno_id>", methods=["DELETE"])
@login_requerido
@rol_requerido("secretaria")
def eliminar_turno(turno_id):
    """Eliminar un turno específico por ID"""
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Verificar si el turno existe
        c.execute("SELECT * FROM turnos WHERE id = ?", (turno_id,))
        turno = c.fetchone()
        
        if not turno:
            return jsonify({"error": "Turno no encontrado"}), 404
        
        # Eliminar el turno
        c.execute("DELETE FROM turnos WHERE id = ?", (turno_id,))
        conn.commit()
        
        return jsonify({"success": True, "mensaje": "Turno eliminado correctamente"})
        
    except sqlite3.Error as e:
        return jsonify({"error": f"Error en la base de datos: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()


@app.route("/api/turnos/estado", methods=["PUT"])
@login_requerido
@rol_permitido(["medico"])
def actualizar_estado_turno():
    data = request.json
    dni_paciente = data.get("dni_paciente")
    fecha = data.get("fecha")
    hora = data.get("hora")
    nuevo_estado = data.get("estado")


    if nuevo_estado not in ["sin atender", "llamado", "atendido", "ausente"]:
        return jsonify({"error": "Estado inválido"}), 400


    turnos = cargar_json(TURNOS_FILE)
    encontrado = False


    for turno in turnos:
        if turno["dni_paciente"] == dni_paciente and turno["fecha"] == fecha and turno["hora"] == hora:
            turno["estado"] = nuevo_estado
            encontrado = True
            break


    if not encontrado:
        return jsonify({"error": "Turno no encontrado"}), 404


    guardar_json(TURNOS_FILE, turnos)
    return jsonify({"mensaje": "Estado actualizado correctamente"})


@app.route("/turnos")
@login_requerido
@rol_permitido(["secretaria", "medico"])
def ver_turnos():
    # Redirigir según el rol
    if session.get("rol") == "medico":
        return render_template("turnos_medico.html")
    else:
        return render_template("pacientes_turnos.html")

@app.route("/turnos/gestion")
@login_requerido
@rol_permitido(["secretaria", "medico", "administrador"])
def gestion_turnos():
    return render_template("pacientes_turnos.html")

@app.route("/api/turnos/medico", methods=["GET"])
@login_requerido
@rol_requerido("medico")
def obtener_turnos_medico():
    print("DEBUG - obtener_turnos_medico iniciado")
    usuario_medico = session.get("usuario")
    print(f"DEBUG - Usuario médico: {usuario_medico}")
    
    try:
        # Usar cargar_json para obtener turnos
        turnos_data = cargar_json(TURNOS_FILE)
        print(f"DEBUG - Turnos cargados: {len(turnos_data)}")
        
        # Filtrar turnos del médico
        turnos_medico = [t for t in turnos_data if t.get("medico") == usuario_medico]
        print(f"DEBUG - Turnos del médico: {len(turnos_medico)}")
        
        return jsonify(turnos_medico)
        
    except Exception as e:
        print(f"ERROR - Error al obtener turnos del médico: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": "Error interno al obtener turnos"}), 500

@app.route("/secretaria")
@login_requerido
@rol_permitido(["secretaria", "administrador"])
def vista_secretaria():
    return render_template("secretaria.html")

@app.route("/agenda")
@login_requerido
@rol_requerido("secretaria")
def ver_agenda():
    return render_template("agenda.html")

@app.route("/calendario")
def calendario():
    return render_template("calendario.html")

@app.route("/test_frontend")
def test_frontend():
    return send_file("test_frontend.html")


def cargar_agenda_desde_db():
    """Carga la agenda desde la base de datos SQLite"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Obtener todos los horarios de la agenda
        c.execute('''
            SELECT medico, dia_semana, horario 
            FROM agenda 
            ORDER BY medico, dia_semana, horario
        ''')
        
        horarios = c.fetchall()
        print(f"DEBUG - cargar_agenda_desde_db: {len(horarios)} horarios encontrados en BD")
        for h in horarios:
            print(f"DEBUG - Horario BD: {h[0]} - {h[1]} - {h[2]}")
        
        conn.close()
        
        # Construir la estructura de agenda
        agenda = {}
        for medico, dia, hora in horarios:
            if medico not in agenda:
                agenda[medico] = {}
            if dia not in agenda[medico]:
                agenda[medico][dia] = []
            agenda[medico][dia].append(hora)
        
        print(f"DEBUG - Agenda construida: {agenda}")
        return agenda
        
    except Exception as e:
        print(f"Error al cargar agenda desde DB: {e}")
        return {}

@app.route("/api/agenda", methods=["GET"])
@login_requerido
@rol_permitido(["secretaria", "medico"])
def obtener_agenda():
    try:
        # Cargar desde base de datos en lugar del archivo JSON
        agenda_data = cargar_agenda_desde_db()
        return jsonify(agenda_data)
    except Exception as e:
        print(f"Error al cargar agenda: {e}")
        return jsonify({"error": "Error al cargar la agenda"}), 500


@app.route("/api/agenda/<medico>/<dia>", methods=["PUT"])
@login_requerido
@rol_requerido("secretaria")
def actualizar_agenda_dia(medico, dia):
    payload = request.json
    # aceptar tanto lista cruda ["10:00", ...] como {"horarios": [...]}
    if isinstance(payload, list):
        nuevos_horarios = payload
    elif isinstance(payload, dict) and isinstance(payload.get("horarios"), list):
        nuevos_horarios = payload["horarios"]
    else:
        return jsonify({"error": "Formato inválido: enviar lista de horarios o {'horarios': [...]}"}), 400

    dia_key = dia.upper()
    if dia_key not in ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES"]:
        return jsonify({"error": "Día inválido"}), 400

    # Persistir directamente en BD
    conn = get_db_connection()
    try:
        with conn:
            conn.execute("DELETE FROM agenda WHERE medico=? AND dia_semana=?", (medico, dia_key))
            for hora in nuevos_horarios:
                conn.execute(
                    "INSERT OR IGNORE INTO agenda (medico, dia_semana, horario) VALUES (?, ?, ?)",
                    (medico, dia_key, hora),
                )
    finally:
        conn.close()

    return jsonify({"mensaje": "Agenda actualizada correctamente"})

@app.route("/api/agenda/<medico>", methods=["PUT"])
@login_requerido
@rol_requerido("secretaria")
def actualizar_agenda_medico(medico):
    """Actualizar todos los horarios de un médico"""
    data = request.json
    print(f"DEBUG - actualizar_agenda_medico: médico={medico}, data={data}")
    
    if not isinstance(data, dict):
        print(f"DEBUG - Error: data no es dict, es {type(data)}")
        return jsonify({"error": "Formato inválido: enviar objeto con días y horarios"}), 400
    
    # Validar días permitidos
    dias_validos = ["lunes", "martes", "miercoles", "jueves", "viernes", "sabado"]
    
    # Persistir directamente en BD
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Eliminar todos los horarios existentes del médico
        print(f"DEBUG - Eliminando horarios existentes para {medico}")
        c.execute("DELETE FROM agenda WHERE medico=?", (medico,))
        
        # Insertar nuevos horarios
        total_insertados = 0
        for dia, horarios in data.items():
            print(f"DEBUG - Procesando día: {dia}, horarios: {horarios}")
            if dia.lower() in dias_validos and isinstance(horarios, list):
                dia_key = dia.upper()
                print(f"DEBUG - Día válido: {dia} -> {dia_key}")
                for hora in horarios:
                    print(f"DEBUG - Insertando: {medico}, {dia_key}, {hora}")
                    c.execute(
                        "INSERT OR IGNORE INTO agenda (medico, dia_semana, horario) VALUES (?, ?, ?)",
                        (medico, dia_key, hora),
                    )
                    total_insertados += 1
            else:
                print(f"DEBUG - Día inválido o horarios no es lista: {dia}, {type(horarios)}")
        
        conn.commit()
        print(f"DEBUG - Total horarios insertados: {total_insertados}")
        
    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print(f"ERROR - Base de datos bloqueada al actualizar agenda: {e}")
            return jsonify({"error": "La base de datos está temporalmente ocupada. Por favor, intente nuevamente en unos segundos."}), 503
        else:
            print(f"ERROR - Error de base de datos al actualizar agenda: {e}")
            return jsonify({"error": "Error interno al actualizar la agenda"}), 500
    except sqlite3.Error as e:
        print(f"ERROR - Error de base de datos al actualizar agenda: {e}")
        return jsonify({"error": "Error interno al actualizar la agenda"}), 500
    except Exception as e:
        print(f"ERROR - Error inesperado al actualizar agenda: {e}")
        return jsonify({"error": "Error interno al actualizar la agenda"}), 500
    finally:
        if conn:
            conn.close()
    
    return jsonify({"mensaje": "Horarios del médico actualizados correctamente"})

@app.route("/api/turnos/<dni>/<fecha>/<hora>", methods=["PUT"])
@login_requerido
@rol_permitido(["secretaria", "medico"])
def editar_turno(dni, fecha, hora):
    data = request.json
    turnos = cargar_json(TURNOS_FILE)
    
    # Encontrar el turno específico
    turno_encontrado = None
    for turno in turnos:
        if turno["dni_paciente"] == dni and turno["fecha"] == fecha and turno["hora"] == hora:
            turno_encontrado = turno
            break
    
    if not turno_encontrado:
        return jsonify({"error": "Turno no encontrado"}), 404
    
    # Actualizar los campos permitidos
    if "nueva_hora" in data:
        nueva_hora = data["nueva_hora"]
        nueva_fecha = data.get("nueva_fecha", fecha)
        # Verificar que la nueva hora no esté ocupada en la fecha correspondiente
        if any(t["medico"] == turno_encontrado["medico"] and t["fecha"] == nueva_fecha and t["hora"] == nueva_hora and 
               not (t["dni_paciente"] == dni and t["fecha"] == fecha and t["hora"] == hora) for t in turnos):
            return jsonify({"error": "La nueva hora ya está ocupada"}), 400
        turno_encontrado["hora"] = nueva_hora
    
    if "nueva_fecha" in data:
        nueva_fecha = data["nueva_fecha"]
        nueva_hora = data.get("nueva_hora", turno_encontrado["hora"])
        # Verificar que la nueva fecha/hora no esté ocupada
        if any(t["medico"] == turno_encontrado["medico"] and t["fecha"] == nueva_fecha and t["hora"] == nueva_hora and 
               not (t["dni_paciente"] == dni and t["fecha"] == fecha and t["hora"] == hora) for t in turnos):
            return jsonify({"error": "La nueva fecha/hora ya está ocupada"}), 400
        turno_encontrado["fecha"] = nueva_fecha
    
    if "nuevo_medico" in data:
        turno_encontrado["medico"] = data["nuevo_medico"]
    
    if "nuevo_estado" in data:
        estados_validos = ["sin atender", "recepcionado", "sala de espera", "llamado", "atendido", "ausente"]
        if data["nuevo_estado"] in estados_validos:
            turno_encontrado["estado"] = data["nuevo_estado"]

    guardar_json(TURNOS_FILE, turnos)
    return jsonify({"mensaje": "Turno actualizado correctamente"})

# ======================= SISTEMA DE PAGOS =======================

@app.route("/api/pagos", methods=["GET"])
@login_requerido
@rol_permitido(["secretaria", "administrador"])
def obtener_pagos():
    pagos = cargar_json(PAGOS_FILE)
    return jsonify(pagos)

@app.route("/api/pagos", methods=["POST"])
@login_requerido
@rol_requerido("secretaria")
def registrar_pago():
    data = request.json
    campos_requeridos = ["dni_paciente", "fecha"]
    
    for campo in campos_requeridos:
        if not data.get(campo):
            return jsonify({"error": f"El campo '{campo}' es requerido"}), 400
        
    # Validar monto (puede ser 0 para obra social)
    try:
        monto = float(data.get("monto", 0))
        if monto < 0:
             return jsonify({"error": "El monto no puede ser negativo"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Monto inválido"}), 400
    
    # Validar tipo de pago (solo para pagos particulares)
    tipo_pago = data.get("tipo_pago", "efectivo")
    if monto > 0 and tipo_pago not in ["efectivo", "transferencia"]:
        return jsonify({"error": "Tipo de pago inválido. Debe ser 'efectivo' o 'transferencia'"}), 400
    
    # Para obra social, el tipo de pago siempre es "obra_social"
    if monto == 0:
        tipo_pago = "obra_social"
    
    # Verificar que el paciente existe
    pacientes = cargar_json(PACIENTES_FILE)
    paciente = next((p for p in pacientes if p["dni"] == data["dni_paciente"]), None)
    
    if not paciente:
        return jsonify({"error": "Paciente no encontrado"}), 404
    
    # Verificar si ya existe un pago para este paciente en esta fecha y hora
    pagos = cargar_json(PAGOS_FILE)
    hora = data.get("hora", "")
    pago_existente = next((p for p in pagos if 
                          p["dni_paciente"] == data["dni_paciente"] and 
                          p["fecha"] == data["fecha"] and 
                          p.get("hora", "") == hora), None)
     
    if pago_existente and hora:
        return jsonify({"error": "Ya existe un pago registrado para este paciente en esta fecha y hora"}), 400
     
    nuevo_pago = {
        "id": None,  # Dejar que SQLite genere el ID automáticamente
        "dni_paciente": data["dni_paciente"],
        "nombre_paciente": f"{paciente.get('nombre', '')} {paciente.get('apellido', '')}".strip(),
        "monto": monto,
        "fecha": data["fecha"],
        "hora": data.get("hora", ""),
        "fecha_registro": datetime.now(timezone_ar).isoformat(),
        "observaciones": data.get("observaciones", ""),
        "obra_social": paciente.get("obra_social", ""),
        "tipo_pago": tipo_pago
    }
    
    pagos.append(nuevo_pago)
    guardar_json(PAGOS_FILE, pagos)
    
    # Obtener el ID generado por la base de datos
    pagos_actualizados = cargar_json(PAGOS_FILE)
    pago_guardado = next((p for p in pagos_actualizados if 
                         p["dni_paciente"] == nuevo_pago["dni_paciente"] and 
                         p["fecha"] == nuevo_pago["fecha"] and 
                         p["hora"] == nuevo_pago["hora"]), None)
    
    if pago_guardado:
        nuevo_pago["id"] = pago_guardado["id"]
    
    return jsonify({"mensaje": "Pago registrado correctamente", "pago": nuevo_pago}), 201

@app.route("/api/pagos/<int:pago_id>", methods=["DELETE"])
@login_requerido
@rol_permitido(["secretaria", "medico"])
def eliminar_pago(pago_id):
    pagos = cargar_json(PAGOS_FILE)
     
    # Filtrar el pago a eliminar
    pagos_filtrados = [p for p in pagos if p.get("id") != pago_id]
     
    if len(pagos_filtrados) == len(pagos):
        return jsonify({"error": "Pago no encontrado"}), 404
     
    guardar_json(PAGOS_FILE, pagos_filtrados)
    return jsonify({"mensaje": "Pago eliminado correctamente"})
 

@app.route("/api/pagos/estadisticas", methods=["GET"])
@login_requerido
@rol_requerido("secretaria")
def obtener_estadisticas_pagos():
    pagos = cargar_json(PAGOS_FILE)
    hoy = date.today()
    # Permitir filtrar por fecha específica
    fecha_param = request.args.get("fecha")
    if fecha_param:
        try:
            fecha_dia = datetime.strptime(fecha_param, "%Y-%m-%d").date()
        except ValueError:
            fecha_dia = hoy
    else:
        fecha_dia = hoy
    mes_param = request.args.get("mes", fecha_dia.strftime("%Y-%m"))
    
    # Filtrar pagos del día
    pagos_hoy = [p for p in pagos if p["fecha"] == fecha_dia.isoformat()]
    total_dia = sum(p["monto"] for p in pagos_hoy)
    
    # Filtrar pagos del mes especificado
    pagos_mes = [p for p in pagos if p["fecha"].startswith(mes_param)]
    total_mes = sum(p["monto"] for p in pagos_mes)
    
    # Estadísticas por tipo de pago del día
    pagos_efectivo_hoy = [p for p in pagos_hoy if p.get("tipo_pago") == "efectivo"]
    pagos_transferencia_hoy = [p for p in pagos_hoy if p.get("tipo_pago") == "transferencia"]
    pagos_obra_social_hoy = [p for p in pagos_hoy if p.get("tipo_pago") == "obra_social"]
    
    total_efectivo_hoy = sum(p["monto"] for p in pagos_efectivo_hoy)
    total_transferencia_hoy = sum(p["monto"] for p in pagos_transferencia_hoy)
    total_obra_social_hoy = sum(p["monto"] for p in pagos_obra_social_hoy)


    # Estadísticas por día del mes
    pagos_por_dia = {}
    pagos_obra_social = 0
    pagos_particulares = 0
     
    for pago in pagos_mes:
        dia = pago["fecha"]
        if dia not in pagos_por_dia:
            pagos_por_dia[dia] = {"cantidad": 0, "monto": 0, "pacientes": []}
         
        pagos_por_dia[dia]["cantidad"] += 1
        pagos_por_dia[dia]["monto"] += pago["monto"]
        pagos_por_dia[dia]["pacientes"].append({
            "nombre": pago["nombre_paciente"],
            "monto": pago["monto"],
            "obra_social": pago.get("obra_social", ""),
            "tipo_pago": pago.get("tipo_pago", "efectivo")
        })
         
        if pago["monto"] == 0:
            pagos_obra_social += 1
        else:
             pagos_particulares += 1
     
    # Ordenar días por fecha
    pagos_por_dia_ordenados = dict(sorted(pagos_por_dia.items()))
    
    return jsonify({
        "total_dia": total_dia,
        "total_mes": total_mes,
        "cantidad_pagos_dia": len(pagos_hoy),
        "cantidad_pagos_mes": len(pagos_mes),
        "pagos_obra_social": pagos_obra_social,
        "pagos_particulares": pagos_particulares,
        "fecha": fecha_dia.isoformat(),
        "mes_consultado": mes_param,
        "detalle_por_dia": pagos_por_dia_ordenados,
        # Nuevas estadísticas por tipo de pago
        "pagos_efectivo_hoy": len(pagos_efectivo_hoy),
        "pagos_transferencia_hoy": len(pagos_transferencia_hoy),
        "pagos_obra_social_hoy": len(pagos_obra_social_hoy),
        "total_efectivo_hoy": total_efectivo_hoy,
        "total_transferencia_hoy": total_transferencia_hoy,
        "total_obra_social_hoy": total_obra_social_hoy
    })
@app.route("/api/pagos/exportar", methods=["GET"])
@login_requerido
@rol_requerido("secretaria")
def exportar_pagos_csv():
    pagos = cargar_json(PAGOS_FILE)
    pacientes = cargar_json(PACIENTES_FILE)

    # Obtener la fecha seleccionada (o hoy por defecto)
    
    fecha_param = request.args.get("fecha")
    if fecha_param:
        try:
            fecha_dia = datetime.strptime(fecha_param, "%Y-%m-%d").date()
        except ValueError:
            fecha_dia = date.today()
    else:
        fecha_dia = date.today()
    
    # Filtrar pagos de la fecha seleccionada
    pagos_dia = [p for p in pagos if p["fecha"] == fecha_dia.isoformat()]
    
    # Calcular subtotales
    subtotal_efectivo = sum(p["monto"] for p in pagos_dia if p.get("tipo_pago") == "efectivo")
    subtotal_transferencia = sum(p["monto"] for p in pagos_dia if p.get("tipo_pago") == "transferencia")
    total = subtotal_efectivo + subtotal_transferencia
    
    # Crear archivo CSV en memoria
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Encabezados
    writer.writerow(['Fecha', 'Apellido', 'Nombre', 'DNI', 'Monto', 'Tipo de Pago', 'Observaciones'])
    
    # Datos
    for pago in pagos_dia:
        paciente = next((p for p in pacientes if p["dni"] == pago["dni_paciente"]), {})
        writer.writerow([
            pago["fecha"],
            paciente.get("apellido", ""),
            paciente.get("nombre", ""),
            pago["dni_paciente"],
            pago.get("tipo_pago", "efectivo"),
            pago.get("observaciones", "")
        ])
    # Fila vacía
    
    writer.writerow([])
    # Subtotales
    writer.writerow(["", "", "", "", "Subtotal Efectivo", subtotal_efectivo, ""])
    writer.writerow(["", "", "", "", "Subtotal Transferencia", subtotal_transferencia, ""])
    writer.writerow(["", "", "", "", "TOTAL", total, ""])

    # Preparar respuesta
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=pagos_{fecha_dia.isoformat()}.csv"
    response.headers["Content-type"] = "text/csv"
    
    return response

@app.route("/api/pacientes/atendidos", methods=["GET"])
@login_requerido
@rol_permitido(["secretaria", "medico"])
def obtener_pacientes_atendidos():
    """Obtiene pacientes que fueron atendidos y aún no tienen pago registrado para una fecha específica"""
    fecha = request.args.get("fecha", date.today().isoformat())
    
    turnos = cargar_json(TURNOS_FILE)
    pacientes = cargar_json(PACIENTES_FILE)
    pagos = cargar_json(PAGOS_FILE)
    
    # Filtrar turnos atendidos en la fecha especificada
    turnos_atendidos = [t for t in turnos if t["fecha"] == fecha and t["estado"] == "atendido"]
    
    # Obtener DNIs que ya tienen pago registrado en esa fecha
    dnis_con_pago = {p["dni_paciente"] for p in pagos if p["fecha"] == fecha}
    
    # Filtrar pacientes atendidos sin pago
    pacientes_sin_pago = []
    for turno in turnos_atendidos:
        if turno["dni_paciente"] not in dnis_con_pago:
            paciente = next((p for p in pacientes if p["dni"] == turno["dni_paciente"]), None)
            if paciente:
                pacientes_sin_pago.append({
                    "dni": paciente["dni"],
                    "nombre": paciente["nombre"],
                    "apellido": paciente["apellido"],
                    "obra_social": paciente.get("obra_social", ""),
                    "hora_turno": turno["hora"],
                    "medico": turno["medico"]
                })
    
    return jsonify(pacientes_sin_pago)

@app.route("/api/pacientes/recepcionados", methods=["GET"])
@login_requerido
@rol_permitido(["secretaria", "medico", "administrador"])
def obtener_pacientes_recepcionados():
    """Obtiene pacientes que están recepcionados y pendientes de pago"""
    fecha = request.args.get("fecha", date.today().isoformat())
    
    turnos = cargar_json(TURNOS_FILE)
    pacientes = cargar_json(PACIENTES_FILE)
    pagos = cargar_json(PAGOS_FILE)
    
    # Filtrar turnos recepcionados en la fecha especificada
    turnos_recepcionados = [t for t in turnos if t.get("fecha") == fecha and t.get("estado") == "recepcionado"]
    
    # Obtener DNIs que ya tienen pago registrado en esa fecha
    dnis_con_pago = {p["dni_paciente"] for p in pagos if p["fecha"] == fecha}
    
    # Filtrar pacientes recepcionados sin pago
    pacientes_recepcionados = []
    for turno in turnos_recepcionados:
        if turno["dni_paciente"] not in dnis_con_pago:
            paciente = next((p for p in pacientes if p["dni"] == turno["dni_paciente"]), None)
            if paciente:
                pacientes_recepcionados.append({
                    "dni": paciente["dni"],
                    "nombre": paciente["nombre"],
                    "apellido": paciente["apellido"],
                    "obra_social": paciente.get("obra_social", ""),
                    "celular": paciente.get("celular", ""),
                    "hora_turno": turno["hora"],
                    "medico": turno["medico"],
                    "fecha": turno["fecha"],
                    "hora_recepcion": ""
                })
    
    # Ordenar por hora de turno
    pacientes_recepcionados.sort(key=lambda p: p.get("hora_turno", "00:00"))
    
    return jsonify(pacientes_recepcionados)

@app.route("/api/pacientes/sala-espera", methods=["GET"])
@login_requerido
@rol_permitido(["secretaria", "medico", "administrador"])
def obtener_pacientes_sala_espera():
    """Obtiene pacientes que están en sala de espera (ya cobrados)"""
    fecha = request.args.get("fecha", date.today().isoformat())
    
    turnos = cargar_json(TURNOS_FILE)
    pacientes = cargar_json(PACIENTES_FILE)
    pagos = cargar_json(PAGOS_FILE)
    
    # Filtrar turnos en sala de espera en la fecha especificada
    turnos_sala_espera = [t for t in turnos if t.get("fecha") == fecha and t.get("estado") == "sala de espera"]
    
    # Obtener información de pagos para estos pacientes
    pacientes_sala_espera = []
    for turno in turnos_sala_espera:
        paciente = next((p for p in pacientes if p["dni"] == turno["dni_paciente"]), None)
        pago = next((p for p in pagos if p["dni_paciente"] == turno["dni_paciente"] and p["fecha"] == fecha), None)
        
        if paciente:
            pacientes_sala_espera.append({
                "dni": paciente["dni"],
                "nombre": paciente["nombre"],
                "apellido": paciente["apellido"],
                "obra_social": paciente.get("obra_social", ""),
                "celular": paciente.get("celular", ""),
                "hora_turno": turno["hora"],
                "medico": turno["medico"],
                "fecha": turno["fecha"],
                "hora_recepcion": "",
                "hora_sala_espera": "",
                "monto_pagado": pago.get("monto", 0) if pago else 0,
                "tipo_pago": pago.get("metodo_pago", "obra_social") if pago else "obra_social",
                "observaciones": pago.get("observaciones", "") if pago else ""
            })
    
    # Ordenar por hora de turno
    pacientes_sala_espera.sort(key=lambda p: p.get("hora_turno", "00:00"))
    
    return jsonify(pacientes_sala_espera)

# ======================= SISTEMA DE RECEPCIÓN =======================

@app.route("/api/turnos/recepcionar", methods=["PUT"])
@login_requerido
@rol_permitido(["secretaria"])
def recepcionar_paciente():
    """Cambiar el estado de un turno a 'recepcionado' cuando llega el paciente"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Cuerpo inválido; enviar JSON"}), 400
    dni_paciente = data.get("dni_paciente")
    fecha = data.get("fecha")
    hora = data.get("hora")
    
    if not all([dni_paciente, fecha, hora]):
        return jsonify({"error": "DNI, fecha y hora son requeridos"}), 400
    
    turnos = cargar_json(TURNOS_FILE)
    
    for turno in turnos:
        if (turno["dni_paciente"] == dni_paciente and 
            turno["fecha"] == fecha and 
            turno["hora"] == hora):
            
            turno["estado"] = "recepcionado"
            
            guardar_json(TURNOS_FILE, turnos)
            return jsonify({"mensaje": "Paciente recepcionado correctamente"})
    
    return jsonify({"error": "Turno no encontrado"}), 404

@app.route("/api/turnos/sala-espera", methods=["PUT"])
@login_requerido
@rol_permitido(["secretaria", "administrador"])
def mover_a_sala_espera():
    """Mover paciente recepcionado a sala de espera y registrar pago"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Cuerpo inválido; enviar JSON"}), 400
    dni_paciente = data.get("dni_paciente")
    fecha = data.get("fecha")
    hora = data.get("hora")
    monto = data.get("monto", 0)
    observaciones = data.get("observaciones", "")
    tipo_pago = data.get("tipo_pago", "efectivo")
     
    if not all([dni_paciente, fecha, hora]):
        return jsonify({"error": "DNI, fecha y hora son requeridos"}), 400
     
    try:
        monto = float(monto)
        if monto < 0:
            return jsonify({"error": "El monto no puede ser negativo"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Monto inválido"}), 400

    if monto == 0:
        tipo_pago = "obra_social"
    elif tipo_pago not in ["efectivo", "transferencia"]:
        return jsonify({"error": "Tipo de pago inválido. Debe ser 'efectivo' o 'transferencia'"}), 400

    # Operar directamente en la BD para evitar inconsistencias y colisiones de IDs
    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # 1) Verificar turno recepcionado
        cur.execute(
            """
            SELECT estado FROM turnos
            WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
            """,
            (dni_paciente, fecha, hora),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Turno no encontrado"}), 404
        if (row["estado"] or "").lower() != "recepcionado":
            return jsonify({"error": "El paciente debe estar recepcionado primero"}), 400
        
        # 2) Verificar paciente
        cur.execute(
            "SELECT nombre, apellido, obra_social FROM pacientes WHERE dni=?",
            (dni_paciente,),
        )
        p = cur.fetchone()
        if not p:
            return jsonify({"error": "Paciente no encontrado"}), 404
     
        # 3) Evitar pago duplicado mismo turno
        cur.execute(
            "SELECT 1 FROM pagos WHERE dni_paciente=? AND fecha=? AND hora=?",
            (dni_paciente, fecha, hora),
        )
        if cur.fetchone():
            return jsonify({"error": "Ya existe un pago registrado para este turno"}), 400

        # 4) Insertar pago (dejar que la BD asigne id)
        cur.execute(
            """
            INSERT INTO pagos (dni_paciente, monto, fecha_pago, metodo_pago, obra_social, observaciones, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dni_paciente,
                monto,
                fecha,
                tipo_pago,
                p["obra_social"] or "",
                observaciones,
                datetime.now(timezone_ar).isoformat(),
            ),
        )

        # 5) Actualizar turno a sala de espera
        cur.execute(
            """
            UPDATE turnos
            SET estado='sala de espera'
            WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
            """,
            (dni_paciente, fecha, hora),
        )

        conn.commit()
        return jsonify({"mensaje": "Paciente movido a sala de espera y pago registrado"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Error al registrar pago: {str(e)}"}), 500
    finally:
        conn.close()
    
@app.route("/api/pagos/cobrar-y-sala", methods=["PUT"])
@login_requerido
@rol_permitido(["secretaria"])
def cobrar_y_mover_a_sala():
    """Cobrar a un paciente recepcionado y moverlo a sala de espera desde gestión de pagos"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Cuerpo inválido; enviar JSON"}), 400
    dni_paciente = data.get("dni_paciente")
    fecha = data.get("fecha")
    monto = data.get("monto", 0)
    observaciones = data.get("observaciones", "")
    tipo_pago = data.get("tipo_pago", "efectivo")
    
    if not all([dni_paciente, fecha]):
        return jsonify({"error": "DNI y fecha son requeridos"}), 400
    
    try:
        monto = float(monto)
        if monto < 0:
            return jsonify({"error": "El monto no puede ser negativo"}), 400
    except (ValueError, TypeError):
        return jsonify({"error": "Monto inválido"}), 400
    
    if monto == 0:
        tipo_pago = "obra_social"
    elif tipo_pago not in ["efectivo", "transferencia"]:
        return jsonify({"error": "Tipo de pago inválido"}), 400

    conn = get_db_connection()
    try:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Buscar turno recepcionado (cualquier hora ese día)
        cur.execute(
            """
            SELECT hora_turno as hora FROM turnos
            WHERE dni_paciente=? AND fecha_turno=? AND estado='recepcionado'
            ORDER BY hora_turno LIMIT 1
            """,
            (dni_paciente, fecha),
        )
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "No se encontró un turno recepcionado para este paciente en esta fecha"}), 404
        hora = row["hora"]

        # Paciente
        cur.execute("SELECT nombre, apellido, obra_social FROM pacientes WHERE dni=?", (dni_paciente,))
        p = cur.fetchone()
        if not p:
            return jsonify({"error": "Paciente no encontrado"}), 404
    
        # Evitar pago duplicado (mismo día)
        cur.execute("SELECT 1 FROM pagos WHERE dni_paciente=? AND fecha_pago=?", (dni_paciente, fecha))
        if cur.fetchone():
            return jsonify({"error": "Ya existe un pago registrado para este paciente en esta fecha"}), 400

        # Insert pago
        cur.execute(
            """
            INSERT INTO pagos (dni_paciente, monto, fecha_pago, metodo_pago, obra_social, observaciones, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dni_paciente,
                monto,
                fecha,
                tipo_pago,
                p["obra_social"] or "",
                observaciones,
                datetime.now(timezone_ar).isoformat(),
            ),
        )

        # Actualizar turno
        cur.execute(
            """
            UPDATE turnos
            SET estado='sala de espera'
            WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
            """,
            (dni_paciente, fecha, hora),
        )

        conn.commit()
        return jsonify({"mensaje": "Pago registrado y paciente movido a sala de espera"})
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Error al registrar pago: {str(e)}"}), 500
    finally:
        conn.close()

@app.route("/api/turnos/dia", methods=["GET"])
@login_requerido
@rol_permitido(["secretaria", "medico", "administrador"])
def obtener_turnos_dia():
    """Obtener todos los turnos de una fecha específica (por defecto hoy)"""
    fecha = request.args.get("fecha", date.today().isoformat())
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Obtener turnos del día desde la base de datos
        c.execute('''
            SELECT t.id, t.medico, t.hora_turno as hora, t.fecha_turno as fecha, t.dni_paciente, t.estado,
                   p.nombre, p.apellido, p.celular
            FROM turnos t
            LEFT JOIN pacientes p ON t.dni_paciente = p.dni
            WHERE t.fecha_turno = ?
            ORDER BY t.hora_turno
        ''', (fecha,))
        
        turnos_dia = []
        for row in c.fetchall():
            turno = {
                "id": row[0],
                "medico": row[1],
                "hora": row[2],
                "fecha": row[3],
                "dni_paciente": row[4],
                "estado": row[5] or "sin atender",
                "paciente": {
                    "nombre": row[6],
                    "apellido": row[7],
                    "celular": row[8]
                } if row[6] else {}
            }
            turnos_dia.append(turno)
        
        conn.close()
        return jsonify(turnos_dia)
        
    except Exception as e:
        print(f"Error al obtener turnos del día: {e}")
        return jsonify({"error": "Error al obtener turnos del día"}), 500

@app.route('/api/turnos/limpiar-vencidos', methods=['POST'])
@login_requerido
@rol_requerido('secretaria')
def limpiar_turnos_vencidos():
    
    turnos = cargar_json(TURNOS_FILE)
    ahora = datetime.now()
    nuevos = []
    eliminados = 0
    for t in turnos:
        fecha_hora_str = f"{t.get('fecha', '')} {t.get('hora', '00:00')}"
        try:
            fecha_hora = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M")
        except Exception:
            nuevos.append(t)
            continue
        if t.get('estado', '').lower() == 'sin atender' and fecha_hora < ahora - timedelta(hours=24):
            eliminados += 1
        else:
            nuevos.append(t)
    guardar_json(TURNOS_FILE, nuevos)
    return jsonify({"eliminados": eliminados, "ok": True})


# ========================== HISTORIAS CLÍNICAS ==================

@app.route("/historias-gestion")
@login_requerido
@rol_requerido("medico")
def ver_historias_gestion():
    return render_template("historias_gestion.html")

@app.route("/api/historias/buscar", methods=["GET"])
@login_requerido
@rol_requerido("medico")
def buscar_historias():
    historias = cargar_json(DATA_FILE)
    pacientes = cargar_json(PACIENTES_FILE)
    
    # Parámetros de búsqueda
    busqueda = request.args.get("busqueda", "").strip().lower()
    pagina = int(request.args.get("pagina", 1))
    por_pagina = int(request.args.get("por_pagina", 10))
    ordenar_por = request.args.get("ordenar_por", "apellido")
    orden = request.args.get("orden", "asc")
    
    # Enriquecer historias con datos del paciente
    historias_enriquecidas = []
    for historia in historias:
        paciente = next((p for p in pacientes if p["dni"] == historia["dni"]), None)
        if paciente:
            historia_completa = historia.copy()
            historia_completa["paciente"] = paciente
            historias_enriquecidas.append(historia_completa)
    
    # Filtrar por búsqueda (apellido, nombre o DNI)
    if busqueda:
        historias_filtradas = []
        for h in historias_enriquecidas:
            paciente = h["paciente"]
            apellido = paciente.get("apellido", "").lower()
            nombre = paciente.get("nombre", "").lower()
            dni = paciente.get("dni", "").lower()
            
            if (busqueda in apellido or 
                busqueda in nombre or 
                busqueda in dni):
                historias_filtradas.append(h)
        historias_enriquecidas = historias_filtradas
    
    # Agrupar por paciente y obtener la última consulta de cada uno
    pacientes_unicos = {}
    for h in historias_enriquecidas:
        dni = h["dni"]
        if dni not in pacientes_unicos:
            pacientes_unicos[dni] = {
                "paciente": h["paciente"],
                "ultima_consulta": h["fecha_consulta"],
                "total_consultas": 1,
                "ultima_historia": h
            }
        else:
            pacientes_unicos[dni]["total_consultas"] += 1
            # Comparar fechas para encontrar la más reciente
            if h["fecha_consulta"] > pacientes_unicos[dni]["ultima_consulta"]:
                pacientes_unicos[dni]["ultima_consulta"] = h["fecha_consulta"]
                pacientes_unicos[dni]["ultima_historia"] = h
    
    # Convertir a lista para ordenamiento
    lista_pacientes = list(pacientes_unicos.values())
    
    # Ordenar
    if ordenar_por == "apellido":
        lista_pacientes.sort(
            key=lambda x: x["paciente"].get("apellido", "").lower(),
            reverse=(orden == "desc")
        )
    elif ordenar_por == "nombre":
        lista_pacientes.sort(
            key=lambda x: x["paciente"].get("nombre", "").lower(),
            reverse=(orden == "desc")
        )
    elif ordenar_por == "fecha":
        lista_pacientes.sort(
            key=lambda x: x["ultima_consulta"],
            reverse=(orden == "desc")
        )
    elif ordenar_por == "dni":
        lista_pacientes.sort(
            key=lambda x: x["paciente"].get("dni", ""),
            reverse=(orden == "desc")
        )
    
    # Paginación
    total = len(lista_pacientes)
    inicio = (pagina - 1) * por_pagina
    fin = inicio + por_pagina
    pacientes_pagina = lista_pacientes[inicio:fin]
    
    total_paginas = (total + por_pagina - 1) // por_pagina
    
    return jsonify({
        "pacientes": pacientes_pagina,
        "total": total,
        "pagina": pagina,
        "total_paginas": total_paginas,
        "por_pagina": por_pagina
    })



# ========================== ADMINISTRADOR ============================

@app.route("/administrador")
@login_requerido
@rol_requerido("administrador")
def vista_administrador():
    return render_template("administrador.html")

@app.route("/api/pagos/estadisticas-admin", methods=["GET"])
@login_requerido
@rol_requerido("administrador")
def obtener_estadisticas_pagos_admin():
    """Obtener estadísticas de pagos para administradores"""
    mes = request.args.get("mes")
    if not mes:
        mes = datetime.now().strftime("%Y-%m")
    
    pagos = cargar_json(PAGOS_FILE)
    pacientes = cargar_json(PACIENTES_FILE)
    
    # Filtrar pagos del mes
    pagos_mes = [p for p in pagos if p.get("fecha", "").startswith(mes)]
    
    # Calcular estadísticas generales
    total_mes = sum(p.get("monto", 0) for p in pagos_mes)
    pagos_particulares = len([p for p in pagos_mes if p.get("monto", 0) > 0])
    pagos_obra_social = len([p for p in pagos_mes if p.get("monto", 0) == 0])
    cantidad_pagos_mes = len(pagos_mes)
    
    # Estadísticas por tipo de pago
    pagos_efectivo = [p for p in pagos_mes if p.get("tipo_pago") == "efectivo"]
    pagos_transferencia = [p for p in pagos_mes if p.get("tipo_pago") == "transferencia"]
    pagos_obra_social_list = [p for p in pagos_mes if p.get("tipo_pago") == "obra_social"]
    
    total_efectivo = sum(p.get("monto", 0) for p in pagos_efectivo)
    total_transferencia = sum(p.get("monto", 0) for p in pagos_transferencia)
    total_obra_social = sum(p.get("monto", 0) for p in pagos_obra_social_list)
    
    
    # Agrupar por día
    detalle_por_dia = {}
    for pago in pagos_mes:
        fecha = pago.get("fecha")
        if fecha not in detalle_por_dia:
            detalle_por_dia[fecha] = {
                "cantidad": 0,
                "monto": 0,
                "pacientes": []
            }
        detalle_por_dia[fecha]["cantidad"] += 1
        detalle_por_dia[fecha]["monto"] += pago.get("monto", 0)
        
        # Buscar datos del paciente
        paciente = next((p for p in pacientes if p["dni"] == pago.get("dni_paciente")), {})
        detalle_por_dia[fecha]["pacientes"].append({
            "nombre": f"{paciente.get('nombre', '')} {paciente.get('apellido', '')}".strip(),
            "monto": pago.get("monto", 0),
            "tipo_pago": pago.get("tipo_pago", "efectivo")
        })
    
    return jsonify({
        "total_mes": total_mes,
        "pagos_particulares": pagos_particulares,
        "pagos_obra_social": pagos_obra_social,
        "cantidad_pagos_mes": cantidad_pagos_mes,
        "detalle_por_dia": detalle_por_dia,
        # Nuevas estadísticas por tipo de pago
        "pagos_efectivo": len(pagos_efectivo),
        "pagos_transferencia": len(pagos_transferencia),
        "pagos_obra_social_count": len(pagos_obra_social_list),
        "total_efectivo": total_efectivo,
        "total_transferencia": total_transferencia,
        "total_obra_social": total_obra_social
    })

@app.route("/api/pagos/exportar-admin", methods=["GET"])
@login_requerido
@rol_requerido("administrador")
def exportar_pagos_csv_admin():
    """Exportar pagos a CSV para administradores"""
    
    pagos = cargar_json(PAGOS_FILE)
    pacientes = cargar_json(PACIENTES_FILE)
    
    fecha_param = request.args.get("fecha")
    mes = request.args.get("mes")
    pagos_filtrados = pagos
    nombre_archivo = "pagos"
    
    if fecha_param:
        try:
            fecha_dia = datetime.strptime(fecha_param, "%Y-%m-%d").date()
        except ValueError:
            fecha_dia = date.today()
        pagos_filtrados = [p for p in pagos if p.get("fecha", "") == fecha_dia.isoformat()]
        nombre_archivo += f"_{fecha_dia.isoformat()}"
    elif mes:
        pagos_filtrados = [p for p in pagos if p.get("fecha", "").startswith(mes)]
        nombre_archivo += f"_{mes}"
    else:
        mes_actual = datetime.now().strftime("%Y-%m")
        pagos_filtrados = [p for p in pagos if p.get("fecha", "").startswith(mes_actual)]
        nombre_archivo += f"_{mes_actual}"
    
    # Calcular subtotales si es por día
    if fecha_param:
        subtotal_efectivo = sum(p["monto"] for p in pagos_filtrados if p.get("tipo_pago") == "efectivo")
        subtotal_transferencia = sum(p["monto"] for p in pagos_filtrados if p.get("tipo_pago") == "transferencia")
        subtotal_obra_social = sum(p["monto"] for p in pagos_filtrados if p.get("tipo_pago") == "obra_social")
        total = subtotal_efectivo + subtotal_transferencia
    
    # Crear CSV
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Fecha', 'DNI', 'Nombre', 'Apellido', 'Monto', 'Tipo de Pago', 'Obra Social', 'Observaciones'])
    
    for pago in pagos_filtrados:
        paciente = next((p for p in pacientes if p["dni"] == pago.get("dni_paciente")), {})
        writer.writerow([
            pago.get("fecha", ""),
            pago.get("dni_paciente", ""),
            paciente.get("nombre", ""),
            paciente.get("apellido", ""),
            pago.get("monto", 0),
            pago.get("tipo_pago", "efectivo"),
            paciente.get("obra_social", ""),
            pago.get("observaciones", "")
        ])
    
    # Subtotales solo si es por día
    
    if fecha_param:
        writer.writerow([])
        writer.writerow(["", "", "", "", "Subtotal Efectivo", subtotal_efectivo, "", ""])
        writer.writerow(["", "", "", "", "Subtotal Transferencia", subtotal_transferencia, "", ""])
        writer.writerow(["", "", "", "", "Subtotal Obra Social", subtotal_obra_social, "", ""])
        writer.writerow(["", "", "", "", "TOTAL", total, "", ""])
    
    output.seek(0)
    return make_response(
        output.getvalue(),
        200,
        {
            'Content-Type': 'text/csv',
            'Content-Disposition': f'attachment; filename={nombre_archivo}.csv'
        }
    )

# ====================================================


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)