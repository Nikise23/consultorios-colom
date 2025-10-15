# Sistema de consultorio médico - Solo SQLite - VERSION CON DEBUG AVANZADO

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
import pytz

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "clave_insegura_dev")

# Configurar sesión persistente
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Configurar zona horaria para Argentina (UTC-3)
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
                time.sleep(delay)
                continue
            raise

# Funciones auxiliares para base de datos SQLite
def cargar_turnos():
    """Cargar turnos desde la base de datos"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("""
            SELECT id, medico, hora_turno, fecha_turno, dni_paciente, estado,
                   tipo_consulta, costo, pagado, observaciones
            FROM turnos
            ORDER BY fecha_turno DESC, hora_turno ASC
        """)
        turnos_data = c.fetchall()
        turnos = []
        for row in turnos_data:
            turno = {
                "id": row[0],
                "medico": row[1],
                "hora_turno": row[2],
                "fecha_turno": row[3],
                "dni_paciente": str(row[4] or ""),
                "estado": row[5],
                "tipo_consulta": row[6],
                "costo": row[7],
                "pagado": row[8],
                "observaciones": row[9]
            }
            # Agregar campos adicionales para compatibilidad
            turno["pago_registrado"] = bool(turno.get("pagado", 0))
            turno["monto_pagado"] = float(turno.get("costo") or 0)
            turnos.append(turno)
        conn.close()
        print(f"DEBUG: {len(turnos)} turnos cargados de BD")
        return turnos
    except Exception as e:
        print(f"Error al cargar turnos: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
    return []

def cargar_pacientes():
    """Cargar pacientes desde la base de datos"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT dni, nombre, apellido, fecha_nacimiento, obra_social, numero_obra_social, celular FROM pacientes")
        pacientes_data = c.fetchall()
        pacientes = []
        for row in pacientes_data:
            paciente = {
                "dni": row[0],
                "nombre": row[1],
                "apellido": row[2],
                "fecha_nacimiento": row[3],
                "obra_social": row[4],
                "numero_obra_social": row[5],
                "celular": row[6]
            }
            # Calcular edad
            if paciente.get("fecha_nacimiento"):
                try:
                    fecha_nac = datetime.strptime(paciente["fecha_nacimiento"], "%Y-%m-%d").date()
                    hoy = date.today()
                    edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
                    paciente["edad"] = edad
                except:
                    paciente["edad"] = 0
            else:
                paciente["edad"] = 0
            
            # Marcar si el paciente está incompleto (datos pendientes)
            paciente["incompleto"] = (
                paciente.get("nombre") == "Pendiente" or 
                paciente.get("apellido") == "Pendiente" or
                not paciente.get("fecha_nacimiento") or
                not paciente.get("obra_social") or
                not paciente.get("celular")
            )
            
            pacientes.append(paciente)
        conn.close()
        print(f"DEBUG: {len(pacientes)} pacientes cargados de BD")
        return pacientes
    except Exception as e:
        print(f"Error al cargar pacientes: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
    return []

def cargar_agenda():
    """Cargar agenda desde la base de datos"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT medico, dia_semana as dia, horario as hora FROM agenda")
        agenda = {}
        total_registros = 0
        for medico, dia, hora in c.fetchall():
            agenda.setdefault(medico, {}).setdefault(dia, []).append(hora)
            total_registros += 1
        
        print(f"DEBUG: {total_registros} registros cargados de agenda BD")
        
        for medico in list(agenda.keys()):
            normalizado = {}
            for dia, horas in agenda[medico].items():
                # Mapear nombres de días para compatibilidad
                dia_upper = dia.upper()
                if dia_upper == 'MIERCOLES':
                    dia_upper = 'MIERCOLES'  # Mantener como MIERCOLES
                else:
                    dia_upper = dia_upper
                normalizado[dia_upper] = sorted(horas)
            agenda[medico] = normalizado
        
        print(f"DEBUG: Agenda procesada para {len(agenda)} médicos")
        conn.close()
        return agenda
    except Exception as e:
        print(f"Error al cargar agenda: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
    return {}

def cargar_pagos():
    """Cargar pagos desde la base de datos"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT id, dni_paciente, monto, fecha_pago as fecha, metodo_pago, obra_social, observaciones, fecha_creacion FROM pagos ORDER BY id")
        pagos_data = c.fetchall()
        pagos = []
        for row in pagos_data:
            pago = {
                "id": row[0],
                "dni_paciente": str(row[1] or ""),
                "monto": float(row[2] or 0),
                "fecha": row[3],
                "metodo_pago": row[4],
                "obra_social": row[5],
                "observaciones": row[6],
                "fecha_creacion": row[7]
            }
            # Agregar campos adicionales para compatibilidad
            pago["nombre_paciente"] = ""
            pago["hora"] = ""
            pago["fecha_registro"] = pago.get("fecha_creacion", "")
            pago["tipo_pago"] = pago.get("metodo_pago", "")
            pagos.append(pago)
        conn.close()
        print(f"DEBUG: {len(pagos)} pagos cargados de BD")
        return pagos
    except Exception as e:
        print(f"Error al cargar pagos: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
    return []

def cargar_pagos_mes_con_pacientes(mes: str):
    """Cargar pagos del mes y enriquecer con datos de paciente."""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            """
            SELECT pay.id, pay.dni_paciente, pay.monto, pay.fecha_pago, pay.metodo_pago,
                   pay.obra_social, pay.observaciones, pay.fecha_creacion,
                   pac.nombre, pac.apellido
            FROM pagos pay
            LEFT JOIN pacientes pac ON pac.dni = pay.dni_paciente
            WHERE pay.fecha_pago LIKE ?
            ORDER BY pay.fecha_pago ASC, pay.id ASC
            """,
            (mes + '%',)
        )
        rows = c.fetchall()
        pagos = []
        for r in rows:
            pagos.append({
                "id": r[0],
                "dni_paciente": str(r[1] or ""),
                "monto": float(r[2] or 0),
                "fecha": r[3],
                "tipo_pago": r[4] or "",
                "obra_social": r[5] or "",
                "observaciones": r[6] or "",
                "fecha_creacion": r[7] or "",
                "nombre_paciente": f"{(r[8] or '').strip()} {(r[9] or '').strip()}".strip()
            })
        return pagos
    finally:
        conn.close()

def cargar_historias():
    """Cargar historias clínicas desde la base de datos"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT dni, consulta_medica, medico, fecha_consulta FROM historias_clinicas")
        historias_data = c.fetchall()
        historias = []
        for row in historias_data:
            historia = {
                "dni": str(row[0] or ""),
                "consulta_medica": row[1],
                "medico": row[2],
                "fecha_consulta": row[3]
            }
            historias.append(historia)
        conn.close()
        print(f"DEBUG: {len(historias)} historias clínicas cargadas de BD")
        return historias
    except Exception as e:
        print(f"Error al cargar historias: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
    return []

def cargar_usuarios_db():
    """Cargar usuarios desde la base de datos"""
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute("SELECT usuario, contrasena, rol FROM usuarios")
        usuarios_data = c.fetchall()
        usuarios = []
        for row in usuarios_data:
            usuarios.append({
                "usuario": row[0],
                "contrasena": row[1],
                "rol": row[2]
            })
        conn.close()
        print(f"DEBUG: {len(usuarios)} usuarios cargados de BD")
        return usuarios
    except Exception as e:
        print(f"Error al cargar usuarios: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
    return []

# Funciones auxiliares
def calcular_edad(fecha_nacimiento):
    """Calcular edad a partir de fecha de nacimiento"""
    try:
        fecha_nac = datetime.strptime(fecha_nacimiento, "%Y-%m-%d").date()
        hoy = date.today()
        edad = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
        return edad
    except ValueError:
        return None
    except TypeError:
        return None

# Decoradores de autenticación
def login_requerido(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("usuario") is None:
            if request.path.startswith("/api/"):
                return jsonify({"error": "No autorizado"}), 401
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function

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

# Rutas principales
@app.route("/")
@app.route("/inicio")
@login_requerido
def inicio():
    rol_usuario = session.get("rol")
    if rol_usuario == "medico":
        return render_template("index.html")
    elif rol_usuario == "secretaria":
        return redirect(url_for("vista_secretaria"))
    elif rol_usuario == "administrador":
        return redirect(url_for("vista_administrador"))
    else:
        return redirect(url_for("login"))

print("DEBUG: REGISTRANDO RUTA /login")
@app.route("/login", methods=["GET", "POST"])
def login():
    print("DEBUG: FUNCION LOGIN EJECUTADA")
    if request.method == "POST":
        print("DEBUG: METODO POST DETECTADO")
        usuario = request.form.get("usuario")
        contrasena = request.form.get("contrasena")
        print(f"LOGIN INTENTO: usuario='{usuario}', contrasena='{contrasena[:3]}...'")
        
        try:
            usuarios = cargar_usuarios_db()
            print(f"USUARIOS CARGADOS: {len(usuarios)}")
            for i, u in enumerate(usuarios):
                print(f"  {i}: {u.get('usuario')} - rol={u.get('rol')}")
                if u.get("usuario") == usuario:
                    print(f"USUARIO ENCONTRADO: {usuario}")
                    hash_contraseña = u.get("contrasena", "")
                    if not hash_contraseña or not hash_contraseña.strip():
                        print(f"HASH VACIO para {usuario}")
                        continue
                    try:
                        print(f"VERIFICANDO HASH para {usuario}")
                        if check_password_hash(hash_contraseña, contrasena):
                            session.permanent = True
                            session["usuario"] = usuario
                            session["rol"] = u.get("rol", "")
                            print(f"LOGIN EXITOSO: {usuario} ({u.get('rol')})")
                            if u.get("rol") == "secretaria":
                                print("REDIRIGIENDO A SECRETARIA")
                                return redirect(url_for("vista_secretaria"))
                            elif u.get("rol") == "administrador":
                                print("REDIRIGIENDO A ADMINISTRADOR")
                                return redirect(url_for("vista_administrador"))
                            else:
                                print("REDIRIGIENDO A INICIO")
                                return redirect(url_for("inicio"))
                        else:
                            print(f"HASH INCORRECTO para {usuario}")
                    except ValueError as e:
                        print(f"ERROR EN HASH: {e}")
                        continue
            print(f"NO SE ENCONTRO USUARIO: {usuario}")
        except Exception as e:
            print(f"ERROR EN LOGIN: {e}")
            import traceback
            traceback.print_exc()
        
        return render_template("login.html", error="Usuario o contraseña incorrectos")
    return render_template("login.html")

@app.route("/logout", methods=["GET", "POST"])
@login_requerido
def logout():
    session.clear()
    return redirect(url_for("login"))

# APIs principales
@app.route("/api/usuarios")
@login_requerido
def api_usuarios():
    usuarios = cargar_usuarios_db()
    return jsonify(usuarios)

@app.route("/api/pacientes", methods=["GET", "POST"])
@login_requerido
def api_pacientes():
    if request.method == "GET":
        pacientes = cargar_pacientes()
        return jsonify(pacientes)
    
    # Registrar paciente (POST)
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Cuerpo inválido; enviar JSON"}), 400

    campos_obligatorios = [
        "nombre", "apellido", "dni", "obra_social",
        "numero_obra_social", "celular", "fecha_nacimiento"
    ]
    for campo in campos_obligatorios:
        if not str(data.get(campo, "")).strip():
            return jsonify({"error": f"El campo '{campo}' es obligatorio"}), 400

    dni_str = str(data.get("dni", "")).strip()
    if not dni_str.isdigit() or len(dni_str) not in (7, 8):
        return jsonify({"error": "DNI inválido (solo números, 7 u 8 dígitos)"}), 400

    # Calcular edad si viene fecha_nacimiento
    if data.get("fecha_nacimiento"):
        try:
            fecha_nac = datetime.strptime(data["fecha_nacimiento"], "%Y-%m-%d").date()
            hoy = date.today()
            data["edad"] = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
        except Exception:
            data["edad"] = 0

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        # Verificar DNI único
        cur.execute("SELECT 1 FROM pacientes WHERE dni = ?", (dni_str,))
        if cur.fetchone():
            return jsonify({"error": "Ya existe un paciente con ese DNI"}), 400

        cur.execute(
            """
            INSERT INTO pacientes (dni, nombre, apellido, fecha_nacimiento, obra_social, numero_obra_social, celular)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                dni_str,
                data["nombre"].strip(),
                data["apellido"].strip(),
                data["fecha_nacimiento"].strip(),
                data["obra_social"].strip(),
                data["numero_obra_social"].strip(),
                data["celular"].strip(),
            ),
        )
        conn.commit()
        return jsonify({"success": True, "mensaje": "Paciente registrado correctamente"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Error al registrar paciente: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/pacientes/<dni>", methods=["PUT"])
@login_requerido
@rol_permitido(["secretaria"])
def actualizar_paciente(dni):
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Cuerpo inválido; enviar JSON"}), 400

    campos_obligatorios = [
        "nombre", "apellido", "dni", "obra_social",
        "numero_obra_social", "celular"
    ]
    for campo in campos_obligatorios:
        if not str(data.get(campo, "")).strip():
            return jsonify({"error": f"El campo '{campo}' es obligatorio"}), 400

    nuevo_dni = str(data.get("dni", "")).strip()
    if not nuevo_dni.isdigit() or len(nuevo_dni) not in (7, 8):
        return jsonify({"error": "DNI inválido (solo números, 7 u 8 dígitos)"}), 400

    if data.get("fecha_nacimiento"):
        try:
            fecha_nac = datetime.strptime(data["fecha_nacimiento"], "%Y-%m-%d").date()
            hoy = date.today()
            data["edad"] = hoy.year - fecha_nac.year - ((hoy.month, hoy.day) < (fecha_nac.month, fecha_nac.day))
        except Exception:
            data["edad"] = 0

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Si cambia el DNI, validar que no exista
        if nuevo_dni != dni:
            cur.execute("SELECT 1 FROM pacientes WHERE dni = ?", (nuevo_dni,))
            if cur.fetchone():
                return jsonify({"error": "Ya existe un paciente con ese DNI"}), 400

        cur.execute(
            """
            UPDATE pacientes
            SET dni = ?, nombre = ?, apellido = ?, fecha_nacimiento = ?, obra_social = ?, numero_obra_social = ?, celular = ?
            WHERE dni = ?
            """,
            (
                nuevo_dni,
                data["nombre"].strip(),
                data["apellido"].strip(),
                data.get("fecha_nacimiento", "").strip(),
                data["obra_social"].strip(),
                data["numero_obra_social"].strip(),
                data["celular"].strip(),
                dni,
            ),
        )
        if cur.rowcount == 0:
            return jsonify({"error": "Paciente no encontrado"}), 404
        conn.commit()
        return jsonify({"mensaje": "Paciente actualizado correctamente"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Error al actualizar paciente: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/pacientes/<dni>", methods=["DELETE"])
@login_requerido
@rol_permitido(["secretaria"])
def eliminar_paciente(dni):
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Evitar eliminar si tiene turnos asociados
        cur.execute("SELECT COUNT(1) FROM turnos WHERE dni_paciente = ?", (dni,))
        cantidad_turnos = cur.fetchone()[0]
        if cantidad_turnos:
            return jsonify({"error": f"No se puede eliminar. Tiene {cantidad_turnos} turno(s) asociado(s)."}), 400

        cur.execute("DELETE FROM pacientes WHERE dni = ?", (dni,))
        if cur.rowcount == 0:
            return jsonify({"error": "Paciente no encontrado"}), 404
        conn.commit()
        return jsonify({"mensaje": "Paciente eliminado correctamente"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Error al eliminar paciente: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/turnos", methods=["GET", "POST"])
@login_requerido
def api_turnos():
    if request.method == "GET":
        turnos = cargar_turnos()
        return jsonify(turnos) 
    elif request.method == "POST":
        return asignar_turno_route()

def asignar_turno_route():
    """Crear nuevo turno"""
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
            "INSERT INTO turnos (medico, hora_turno, fecha_turno, dni_paciente, estado, tipo_consulta, costo, observaciones) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (data["medico"], data["hora"], data["fecha"], data["dni_paciente"], 
             data.get("estado", "sin atender"), data.get("tipo_consulta", ""), 
             data.get("costo", 0), data.get("observaciones", ""))
        )
        
        # Obtener el ID del turno recién creado
        turno_id = c.lastrowid
        conn.commit()

        return jsonify({"success": True, "mensaje": "Turno asignado correctamente", "turno_id": turno_id}), 201

    except sqlite3.OperationalError as e:
        if "database is locked" in str(e):
            print(f"ERROR - Base de datos bloqueada al asignar turno: {e}")
            return jsonify({"error": "La base de datos está temporalmente ocupada. Por favor, intente nuevamente en unos segundos."}), 503
        else:
            print(f"ERROR - Error de base de datos al asignar turno: {e}")
            return jsonify({"error": "Error interno al asignar el turno"}), 500
    except Exception as e:
        print(f"ERROR - Error inesperado al asignar turno: {e}")
        return jsonify({"error": "Error interno al asignar el turno"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/agenda", methods=["GET"])
@login_requerido
@rol_permitido(["secretaria", "medico", "administrador"])
def obtener_agenda():
    try:
        agenda_data = cargar_agenda()
        return jsonify(agenda_data)
    except Exception as e:
        print(f"Error al cargar agenda: {e}")
        return jsonify({"error": "Error al cargar la agenda"}), 500

@app.route("/api/agenda/<medico>", methods=["PUT"])
@login_requerido
@rol_permitido(["secretaria", "administrador"])
def actualizar_agenda_medico(medico):
    """Reemplaza la agenda completa de un médico.
    Body esperado: { "Lunes": ["08:00", ...], "MARTES": ["09:00", ...], ... }
    Acepta claves de días en español en cualquier casing, y las normaliza a mayúsculas.
    """
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Cuerpo inválido; enviar JSON"}), 400

    # Normalizar claves de días
    mapa_dias = {
        "LUNES": "LUNES", "Lunes": "LUNES", "lunes": "LUNES",
        "MARTES": "MARTES", "Martes": "MARTES", "martes": "MARTES",
        "MIERCOLES": "MIERCOLES", "Miércoles": "MIERCOLES", "Miércoles".upper(): "MIERCOLES", "miercoles": "MIERCOLES",
        "JUEVES": "JUEVES", "Jueves": "JUEVES", "jueves": "JUEVES",
        "VIERNES": "VIERNES", "Viernes": "VIERNES", "viernes": "VIERNES",
        "SABADO": "SABADO", "Sábado": "SABADO", "sabado": "SABADO",
        "DOMINGO": "DOMINGO", "Domingo": "DOMINGO", "domingo": "DOMINGO",
    }

    agenda_normalizada = {}
    for dia, horas in data.items():
        dia_norm = mapa_dias.get(str(dia), str(dia).upper())
        if not isinstance(horas, list):
            return jsonify({"error": f"El valor para '{dia}' debe ser una lista de horas"}), 400
        # Filtrar strings no vacíos
        horas_validas = [h for h in horas if isinstance(h, str) and h.strip()]
        agenda_normalizada[dia_norm] = horas_validas

    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Limpiar agenda previa del médico
        cur.execute("DELETE FROM agenda WHERE medico = ?", (medico,))

        # Insertar nueva agenda
        for dia_semana, horas in agenda_normalizada.items():
            for hora in horas:
                cur.execute(
                    "INSERT INTO agenda (medico, dia_semana, horario) VALUES (?, ?, ?)",
                    (medico, dia_semana, hora)
                )

        conn.commit()
        return jsonify({"success": True, "mensaje": "Agenda actualizada correctamente"})
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Error al actualizar agenda: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/pagos", methods=["GET", "POST"])
@login_requerido
def api_pagos():
    if request.method == "GET":
        pagos = cargar_pagos()
        return jsonify(pagos)
    
    elif request.method == "POST":
        # Crear nuevo pago
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({"error": "Cuerpo inválido; enviar JSON"}), 400
        
        dni_paciente = data.get("dni_paciente")
        monto = data.get("monto", 0)
        fecha_pago = data.get("fecha")
        tipo_pago = data.get("tipo_pago", "efectivo")
        observaciones = data.get("observaciones", "")
        obra_social = data.get("obra_social", "")
        
        # Validaciones
        if not dni_paciente:
            return jsonify({"error": "DNI del paciente es requerido"}), 400
        
        if not fecha_pago:
            return jsonify({"error": "Fecha es requerida"}), 400
        
        try:
            monto = float(monto)
            if monto < 0:
                return jsonify({"error": "El monto no puede ser negativo"}), 400
        except (ValueError, TypeError):
            return jsonify({"error": "Monto inválido"}), 400
    
        if tipo_pago not in ["efectivo", "transferencia", "obra_social"]:
            return jsonify({"error": "Tipo de pago inválido"}), 400
        
        conn = get_db_connection()
        try:
            cur = conn.cursor()
            
            # Verificar que existe el paciente
            cur.execute("SELECT id FROM pacientes WHERE dni = ?", (dni_paciente,))
            paciente = cur.fetchone()
            if not paciente:
                return jsonify({"error": "Paciente no encontrado"}), 404
    
            # Insertar el pago
            cur.execute("""
                INSERT INTO pagos (dni_paciente, monto, fecha_pago, metodo_pago, obra_social, observaciones, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                dni_paciente,
                monto,
                fecha_pago,
                tipo_pago,
                obra_social,
                observaciones,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            pagos_id = cur.lastrowid
            
            return jsonify({
                "success": True,
                "mensaje": "Pago registrado correctamente",
                "pago_id": pagos_id
            })
            
        except Exception as e:
            return jsonify({"error": f"Error al registrar pago: {str(e)}"}), 500
        finally:
            if conn:
                conn.close()

@app.route("/api/pagos/<int:pago_id>", methods=["DELETE"])
@login_requerido
@rol_permitido(["secretaria", "medico"])
def eliminar_pago(pago_id):
    """Eliminar un pago específico por ID"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar si el pago existe
        cur.execute("SELECT id FROM pagos WHERE id = ?", (pago_id,))
        pago = cur.fetchone()
        
        if not pago:
            return jsonify({"error": "Pago no encontrado"}), 404
     
        # Eliminar el pago
        cur.execute("DELETE FROM pagos WHERE id = ?", (pago_id,))
        conn.commit()
        
        return jsonify({
            "success": True, 
            "mensaje": "Pago eliminado correctamente"
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Error al eliminar pago: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/turnos/medico", methods=["GET"])
@login_requerido
@rol_requerido("medico")
def obtener_turnos_medico():
    usuario_medico = session.get("usuario")
    
    conn = None
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("""
            SELECT t.*, p.nombre, p.apellido, p.celular, p.obra_social
            FROM turnos t
            LEFT JOIN pacientes p ON t.dni_paciente = p.dni
            WHERE t.medico = ?
            ORDER BY t.fecha_turno, t.hora_turno
        """, (usuario_medico,))
        
        turnos_data = c.fetchall()
        
        turnos_medico = []
        for row in turnos_data:
            turno = {
                'id': row[0],
                'dni_paciente': row[1],
                'medico': row[2],
                'fecha': row[3],  # Cambiado de fecha_turno a fecha
                'hora': row[4],   # Cambiado de hora_turno a hora
                'estado': row[5] if row[5] else 'sin atender',
                'tipo_consulta': row[6] if row[6] else '',
                'costo': row[7] if row[7] else 0,
                'pagado': row[8] if row[8] else 0,
                'observaciones': row[9] if row[9] else '',
                'fecha_creacion': row[10] if row[10] else '',
                'paciente': {
                    'nombre': row[11] if row[11] else '',
                    'apellido': row[12] if row[12] else '',
                    'celular': row[13] if row[13] else '',
                    'obra_social': row[14] if len(row) > 14 and row[14] else ''
                }
            }
            turnos_medico.append(turno)

        if conn:
            conn.close()
        return jsonify(turnos_medico)
        
    except Exception as e:
        print(f"ERROR - Error al obtener turnos del médico: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.close()
        return jsonify({"error": "Error interno al obtener turnos"}), 500

@app.route("/api/turnos/dia")
@login_requerido
def obtener_turnos_dia():
    fecha = request.args.get("fecha", date.today().isoformat())
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute('''
            SELECT t.id, t.medico, t.hora_turno as hora, t.fecha_turno as fecha, t.dni_paciente, t.estado,
                   p.nombre, p.apellido, p.celular, p.obra_social
            FROM turnos t
            LEFT JOIN pacientes p ON t.dni_paciente = p.dni
            WHERE t.fecha_turno = ?
            ORDER BY t.hora_turno
        ''', (fecha,))
        
        turnos_dia = []
        for row in c.fetchall():
            paciente_nombre = row[6] if row[6] else ''
            paciente_apellido = row[7] if row[7] else ''
            
            print(f"DEBUG Turno {row[0]}: DNI={row[4]}, Nombre='{paciente_nombre}', Apellido='{paciente_apellido}'")
            
            turno = {
                'id': row[0],
                'medico': row[1],
                'hora': row[2],
                'fecha': row[3],
                'dni_paciente': row[4],
                'estado': row[5],
                'paciente': {
                    'nombre': paciente_nombre,
                    'apellido': paciente_apellido,
                    'celular': row[8] if row[8] else '',
                    'obra_social': row[9] if row[9] else ''
                }
            }
            turnos_dia.append(turno)

        conn.close()
        print(f"DEBUG: Devolviendo {len(turnos_dia)} turnos para fecha {fecha}")
        return jsonify(turnos_dia)
        
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return jsonify({"error": "Error al obtener turnos"}), 500

@app.route("/api/session-info")
@login_requerido
def session_info():
    return jsonify({
        "usuario": session.get("usuario"),
        "rol": session.get("rol")
    })

# ========================== REPORTES ADMIN ===========================

@app.route("/api/reportes/turnos")
@login_requerido
@rol_requerido("administrador")
def reportes_turnos():
    """Reporte de turnos en rango (totales, atendidos, ausentes, por médico y por día)."""
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")
    # Defaults: último mes
    if not fecha_fin:
        fecha_fin = date.today().isoformat()
    if not fecha_inicio:
        d = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        inicio = d.replace(day=1)
        fecha_inicio = inicio.isoformat()

    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            """
            SELECT medico, fecha_turno, estado
            FROM turnos
            WHERE fecha_turno BETWEEN ? AND ?
            """,
            (fecha_inicio, fecha_fin)
        )
        rows = c.fetchall()

        total = len(rows)
        atendidos = sum(1 for r in rows if (r[2] or '').lower() == 'atendido')
        ausentes = sum(1 for r in rows if (r[2] or '').lower() == 'ausente')
        pendientes = total - atendidos - ausentes
        porcentaje_atencion = round((atendidos / total) * 100, 1) if total else 0.0
        porcentaje_ausencias = round((ausentes / total) * 100, 1) if total else 0.0

        stats_por_medico = {}
        stats_por_dia = {}
        for medico, fecha, estado in rows:
            # por médico
            m = stats_por_medico.setdefault(medico or 'Sin asignar', {"total": 0, "atendidos": 0, "ausentes": 0})
            m["total"] += 1
            if (estado or '').lower() == 'atendido':
                m["atendidos"] += 1
            elif (estado or '').lower() == 'ausente':
                m["ausentes"] += 1
            # por día
            d = stats_por_dia.setdefault(fecha, {"total": 0, "atendidos": 0, "ausentes": 0})
            d["total"] += 1
            if (estado or '').lower() == 'atendido':
                d["atendidos"] += 1
            elif (estado or '').lower() == 'ausente':
                d["ausentes"] += 1

        return jsonify({
            "total_turnos": total,
            "turnos_atendidos": atendidos,
            "turnos_ausentes": ausentes,
            "turnos_pendientes": pendientes,
            "porcentaje_atencion": porcentaje_atencion,
            "porcentaje_ausencias": porcentaje_ausencias,
            "stats_por_medico": stats_por_medico,
            "stats_por_dia": stats_por_dia,
        })
    finally:
        conn.close()

@app.route("/api/reportes/ocupacion")
@login_requerido
@rol_requerido("administrador")
def reportes_ocupacion():
    """Reporte básico de ocupación de agenda: slots disponibles vs ocupados en rango."""
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")
    if not fecha_fin:
        fecha_fin = date.today().isoformat()
    if not fecha_inicio:
        d = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        inicio = d - timedelta(days=6)
        fecha_inicio = inicio.isoformat()

    conn = get_db_connection()
    c = conn.cursor()
    try:
        # Slots configurados por médico y día
        c.execute("SELECT DISTINCT medico FROM agenda")
        medicos = [row[0] for row in c.fetchall()]

        # Contabilizar slots disponibles por médico/día del período
        ocupacion_por_medico = {m: {"slots_disponibles": 0, "slots_ocupados": 0, "porcentaje_ocupacion": 0} for m in medicos}
        ocupacion_por_dia = {}

        # Construir mapa de agenda: medico -> dia_semana -> horas
        c.execute("SELECT medico, dia_semana, horario FROM agenda")
        agenda_rows = c.fetchall()
        agenda_map = {}
        for med, dia, hora in agenda_rows:
            agenda_map.setdefault(med, {}).setdefault(dia.upper(), []).append(hora)

        # Helper día semana
        def dia_es_de_fecha(fecha_iso: str) -> str:
            dt = datetime.strptime(fecha_iso, "%Y-%m-%d").date()
            mapping = {0: 'LUNES', 1: 'MARTES', 2: 'MIERCOLES', 3: 'JUEVES', 4: 'VIERNES', 5: 'SABADO', 6: 'DOMINGO'}
            return mapping[dt.weekday()]

        # Recorrer días del rango
        dt_ini = datetime.strptime(fecha_inicio, "%Y-%m-%d").date()
        dt_fin = datetime.strptime(fecha_fin, "%Y-%m-%d").date()

        c.execute(
            """
            SELECT medico, fecha_turno, hora_turno
            FROM turnos
            WHERE fecha_turno BETWEEN ? AND ?
            """,
            (fecha_inicio, fecha_fin)
        )
        turnos_rows = c.fetchall()
        ocupados_idx = {(med, f, h) for med, f, h in turnos_rows}

        current = dt_ini
        while current <= dt_fin:
            fecha_str = current.isoformat()
            dia_semana = dia_es_de_fecha(fecha_str)
            day_stats = ocupacion_por_dia.setdefault(fecha_str, {"slots_disponibles": 0, "slots_ocupados": 0, "porcentaje_ocupacion": 0})
            for med in medicos:
                horas = (agenda_map.get(med, {}).get(dia_semana, []))
                day_stats["slots_disponibles"] += len(horas)
                ocupacion_por_medico[med]["slots_disponibles"] += len(horas)
                for h in horas:
                    if (med, fecha_str, h) in ocupados_idx:
                        day_stats["slots_ocupados"] += 1
                        ocupacion_por_medico[med]["slots_ocupados"] += 1
            # porcentaje por día
            disp = day_stats["slots_disponibles"]
            day_stats["porcentaje_ocupacion"] = round((day_stats["slots_ocupados"] / disp) * 100) if disp else 0
            current += timedelta(days=1)

        # porcentaje por médico
        for med, st in ocupacion_por_medico.items():
            disp = st["slots_disponibles"]
            st["porcentaje_ocupacion"] = round((st["slots_ocupados"] / disp) * 100) if disp else 0

        total_disp = sum(st["slots_disponibles"] for st in ocupacion_por_dia.values())
        total_oc = sum(st["slots_ocupados"] for st in ocupacion_por_dia.values())
        ocupacion_promedio = round((total_oc / total_disp) * 100) if total_disp else 0

        return jsonify({
            "ocupacion_promedio": ocupacion_promedio,
            "total_slots_disponibles": total_disp,
            "total_slots_ocupados": total_oc,
            "ocupacion_por_medico": ocupacion_por_medico,
            "ocupacion_por_dia": ocupacion_por_dia,
        })
    finally:
        conn.close()

@app.route("/api/reportes/pacientes")
@login_requerido
@rol_requerido("administrador")
def reportes_pacientes():
    """Resumen de pacientes: total, edad promedio y distribuciones."""
    pacientes = cargar_pacientes()
    total = len(pacientes)
    edades = [p.get("edad", 0) or 0 for p in pacientes if isinstance(p.get("edad"), int)]
    promedio = round(sum(edades) / len(edades)) if edades else 0

    # obras sociales
    obras = {}
    for p in pacientes:
        os_name = (p.get("obra_social") or "Sin obra social").strip() or "Sin obra social"
        obras[os_name] = obras.get(os_name, 0) + 1

    # rangos de edad
    rangos_def = [(0, 12), (13, 19), (20, 39), (40, 59), (60, 120)]
    rangos = {f"{a}-{b}": 0 for a, b in rangos_def}
    for e in edades:
        for a, b in rangos_def:
            if a <= e <= b:
                rangos[f"{a}-{b}"] += 1
                break

    # pacientes más activos por cantidad de turnos
    conn = get_db_connection()
    c = conn.cursor()
    try:
        c.execute(
            """
            SELECT p.nombre || ' ' || p.apellido as nombre, COUNT(t.id) as cnt
            FROM pacientes p
            LEFT JOIN turnos t ON t.dni_paciente = p.dni
            GROUP BY p.dni
            ORDER BY cnt DESC
            LIMIT 10
            """
        )
        top = [{"nombre": row[0] or "", "turnos": row[1] or 0} for row in c.fetchall()]
    finally:
        conn.close()

    return jsonify({
        "total_pacientes": total,
        "estadisticas_edad": {"promedio": promedio, "rangos": rangos},
        "pacientes_sin_turnos": sum(1 for p in pacientes if p.get("incompleto")),
        "obras_sociales": obras,
        "pacientes_activos": top,
    })

# ====================== DESCARGA DE BASE DE DATOS (ADMIN) ======================

@app.route("/descargar-db", methods=["GET"])
@login_requerido
@rol_requerido("administrador")
def descargar_db():
    """Permite a administradores descargar el archivo SQLite actual."""
    db_path = os.path.join("data", "consultorio.db")
    if not os.path.exists(db_path):
        return jsonify({"error": "Base de datos no encontrada"}), 404
    nombre = f"consultorio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    return send_file(db_path, mimetype="application/octet-stream", as_attachment=True, download_name=nombre)

@app.route("/api/reportes/atenciones")
@login_requerido
@rol_requerido("administrador")
def reportes_atenciones():
    """Reporte de atenciones por médico con filtros y exportación CSV.
    Params: fecha_inicio, fecha_fin, medico (opcional), obra_social (opcional), export=csv (opcional)
    """
    fecha_inicio = request.args.get("fecha_inicio")
    fecha_fin = request.args.get("fecha_fin")
    medico = request.args.get("medico", "").strip()
    obra_social = request.args.get("obra_social", "").strip()
    export = request.args.get("export", "").lower() == "csv"

    # Defaults al mes actual si faltan fechas
    if not fecha_fin:
        fecha_fin = date.today().isoformat()
    if not fecha_inicio:
        d = datetime.strptime(fecha_fin, "%Y-%m-%d").date()
        fecha_inicio = d.replace(day=1).isoformat()

    conn = get_db_connection()
    c = conn.cursor()
    try:
        query = [
            "SELECT p.dni, p.nombre, p.apellido, p.obra_social, p.numero_obra_social, COUNT(1) as atenciones",
            "FROM turnos t",
            "INNER JOIN pacientes p ON p.dni = t.dni_paciente",
            "WHERE t.estado = 'atendido' AND t.fecha_turno BETWEEN ? AND ?",
        ]
        params = [fecha_inicio, fecha_fin]
        if medico:
            query.append("AND t.medico = ?")
            params.append(medico)
        if obra_social:
            query.append("AND (p.obra_social = ?)")
            params.append(obra_social)
        query.append("GROUP BY p.dni, p.nombre, p.apellido, p.obra_social, p.numero_obra_social")
        query.append("ORDER BY p.apellido, p.nombre")

        sql = "\n".join(query)
        c.execute(sql, tuple(params))
        rows = c.fetchall()

        detalles = []
        total_atenciones = 0
        for dni, nombre, apellido, os, nro_os, atenciones in rows:
            detalles.append({
                "dni": str(dni),
                "nombre": nombre or "",
                "apellido": apellido or "",
                "obra_social": os or "",
                "numero_obra_social": nro_os or "",
                "atenciones": int(atenciones or 0),
            })
            total_atenciones += int(atenciones or 0)

        if export:
            # Exportar CSV
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(["DNI", "Nombre", "Apellido", "Obra Social", "N° Obra Social", "Atenciones"])
            for d in detalles:
                writer.writerow([d["dni"], d["nombre"], d["apellido"], d["obra_social"], d["numero_obra_social"], d["atenciones"]])

            csv_data = output.getvalue().encode("utf-8")
            mem = io.BytesIO(csv_data)
            mem.seek(0)
            nombre_archivo = f"atenciones_{(medico or 'todos').replace(' ', '_')}_{fecha_inicio}_a_{fecha_fin}.csv"
            return send_file(mem, mimetype="text/csv", as_attachment=True, download_name=nombre_archivo)

        return jsonify({
            "medico": medico,
            "obra_social": obra_social,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "total_pacientes": len(detalles),
            "total_atenciones": total_atenciones,
            "detalles": detalles,
        })
    finally:
        conn.close()


@app.route("/api/session-debug")
def session_debug():
    """Debug temporal para ver el estado de la sesión"""
    return jsonify({
        "session_usuario": session.get("usuario"),
        "session_rol": session.get("rol"),
        "session_permanent": session.permanent if hasattr(session, 'permanent') else 'No info',
        "session_dict": dict(session),
        "cookies": dict(request.cookies)
    })

@app.route("/api/pagos/estadisticas")
@login_requerido
def estadisticas_pagos():
    """Obtener estadísticas de pagos completas para dashboard de secretaria"""
    fecha = request.args.get("fecha", date.today().isoformat())
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Total del día
        c.execute("SELECT COALESCE(SUM(monto), 0), COUNT(*) FROM pagos WHERE fecha_pago = ?", (fecha,))
        row_dia = c.fetchone()
        total_dia = float(row_dia[0])
        cantidad_pagos_dia = row_dia[1]
        
        # Total del mes
        mes_actual = fecha[:7]  # YYYY-MM
        c.execute("SELECT COALESCE(SUM(monto), 0) FROM pagos WHERE fecha_pago LIKE ?", (mes_actual + '%',))
        total_mes = float(c.fetchone()[0])
        
        # Efectivo del día
        c.execute("SELECT COALESCE(SUM(monto), 0), COUNT(*) FROM pagos WHERE fecha_pago = ? AND metodo_pago = 'efectivo'", (fecha,))
        row_efectivo = c.fetchone()
        total_efectivo_hoy = float(row_efectivo[0])
        pagos_efectivo_hoy = row_efectivo[1]
        
        # Transferencias del día
        c.execute("SELECT COALESCE(SUM(monto), 0), COUNT(*) FROM pagos WHERE fecha_pago = ? AND metodo_pago = 'transferencia'", (fecha,))
        row_transfer = c.fetchone()
        total_transferencia_hoy = float(row_transfer[0])
        pagos_transferencia_hoy = row_transfer[1]
        
        conn.close()
        
        return jsonify({
            "total_dia": total_dia,
            "total_mes": total_mes,
            "cantidad_pagos_dia": cantidad_pagos_dia,
            "total_efectivo_hoy": total_efectivo_hoy,
            "pagos_efectivo_hoy": pagos_efectivo_hoy,
            "total_transferencia_hoy": total_transferencia_hoy,
            "pagos_transferencia_hoy": pagos_transferencia_hoy,
            "fecha": fecha
        })
        
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return jsonify({"error": "Error al obtener estadísticas"}), 500

@app.route("/api/pacientes/recepcionados")
@login_requerido
def pacientes_recepcionados():
    """Obtener pacientes recepcionados en una fecha"""
    fecha = request.args.get("fecha", date.today().isoformat())
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("""
            SELECT DISTINCT p.dni, p.nombre, p.apellido, p.celular
            FROM pacientes p
            INNER JOIN turnos t ON p.dni = t.dni_paciente  
            WHERE t.fecha_turno = ? AND t.estado = 'recepcionado'
            ORDER BY p.apellido, p.nombre
        """, (fecha,))
        
        pacientes = []
        for row in c.fetchall():
            pacientes.append({
                "dni": row[0],
                "nombre": row[1],
                "apellido": row[2], 
                "celular": row[3]
            })
        
        conn.close()
        return jsonify(pacientes)
        
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return jsonify({"error": "Error al obtener pacientes"}), 500

@app.route("/api/pacientes/sala-espera")
@login_requerido
def pacientes_sala_espera():
    """Obtener pacientes en sala de espera en una fecha"""
    fecha = request.args.get("fecha", date.today().isoformat())
    
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        c.execute("""
            SELECT DISTINCT t.hora_turno, t.medico, p.dni, p.nombre, p.apellido, p.celular,
                   pay.monto, pay.metodo_pago, pay.fecha_pago, pay.obra_social, pay.fecha_creacion
            FROM turnos t
            LEFT JOIN pacientes p ON t.dni_paciente = p.dni
            LEFT JOIN pagos pay ON pay.dni_paciente = p.dni AND pay.fecha_pago = ?
            WHERE t.fecha_turno = ? AND t.estado = 'sala de espera'  
            ORDER BY t.hora_turno, p.apellido, p.nombre
        """, (fecha, fecha))
        
        pacientes = []
        for row in c.fetchall():
            # Extraer hora de la fecha_creacion del pago
            hora_cobro = ""
            if row[10]:  # fecha_creacion
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(row[10].replace('Z', '+00:00'))
                    hora_cobro = dt.strftime("%H:%M")
                except:
                    hora_cobro = ""
            
            pacientes.append({
                "hora": row[0],
                "medico": row[1],
                "dni": row[2],
                "nombre": row[3], 
                "apellido": row[4],
                "celular": row[5],
                "monto_pagado": row[6] if row[6] else 0,
                "tipo_pago": row[7] if row[7] else "",
                "fecha_pago": row[8] if row[8] else "",
                "obra_social": row[9] if row[9] else "",
                "hora_cobro": hora_cobro
            })
        
        conn.close()
        return jsonify(pacientes)
        
    except Exception as e:
        if 'conn' in locals():
            conn.close()
        return jsonify({"error": "Error al obtener pacientes"}), 500

# Rutas de vistas
@app.route("/secretaria")
@login_requerido
@rol_permitido(["secretaria", "administrador"])
def vista_secretaria():
    return render_template("secretaria.html")

@app.route("/administrador")
@login_requerido
@rol_requerido("administrador")
def vista_administrador():
    return render_template("administrador.html")

@app.route("/turnos")
@login_requerido
@rol_permitido(["secretaria", "medico", "administrador"])
def gestion_turnos():
    return render_template("pacientes_turnos.html")

@app.route("/turnos-medico")
@login_requerido
@rol_permitido(["medico"])
def turnos_medico():
    return render_template("turnos_medico.html")

@app.route("/calendario")
@login_requerido
@rol_permitido(["secretaria", "administrador"])
def calendario():
    return render_template("calendario.html")

@app.route("/pacientes")
@login_requerido
@rol_permitido(["secretaria", "medico", "administrador"])
def pacientes():
    return render_template("pacientes.html")

@app.route("/agenda")
@login_requerido
@rol_requerido("secretaria")
def agenda():
    return render_template("agenda.html")

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
    
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Verificar que existe el turno
        cur.execute("""
            SELECT estado FROM turnos 
            WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
        """, (dni_paciente, fecha, hora))
        
        turno = cur.fetchone()
        if not turno:
            return jsonify({"error": "Turno no encontrado"}), 404
        
        # Actualizar estado a 'recepcionado'
        cur.execute("""
            UPDATE turnos 
            SET estado='recepcionado'
            WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
        """, (dni_paciente, fecha, hora))
        
        conn.commit()
        return jsonify({"mensaje": "Paciente recepcionado correctamente"})
    
    except Exception as e:
        return jsonify({"error": f"Error al recepcionar paciente: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

# ========================== ADMINISTRADOR ============================

@app.route("/api/pagos/estadisticas-admin", methods=["GET"])
@login_requerido
@rol_requerido("administrador")
def obtener_estadisticas_pagos_admin():
    """Estadísticas mensuales de pagos para panel de administrador."""
    mes = request.args.get("mes")
    if not mes:
        mes = datetime.now().strftime("%Y-%m")

    pagos_mes = cargar_pagos_mes_con_pacientes(mes)

    total_mes = sum(p.get("monto", 0) for p in pagos_mes)
    pagos_particulares = sum(1 for p in pagos_mes if (p.get("monto", 0) or 0) > 0)
    pagos_obra_social = sum(1 for p in pagos_mes if (p.get("monto", 0) or 0) == 0)
    cantidad_pagos_mes = len(pagos_mes)

    pagos_efectivo = [p for p in pagos_mes if (p.get("tipo_pago") or "").lower() == "efectivo"]
    pagos_transferencia = [p for p in pagos_mes if (p.get("tipo_pago") or "").lower() == "transferencia"]
    pagos_obra_social_list = [p for p in pagos_mes if (p.get("tipo_pago") or "").lower() == "obra_social" or p.get("monto", 0) == 0]

    total_efectivo = sum(p.get("monto", 0) for p in pagos_efectivo)
    total_transferencia = sum(p.get("monto", 0) for p in pagos_transferencia)
    total_obra_social = sum(p.get("monto", 0) for p in pagos_obra_social_list)

    # Detalle por día
    detalle_por_dia = {}
    for pago in pagos_mes:
        fecha = pago.get("fecha")
        if not fecha:
            continue
        if fecha not in detalle_por_dia:
            detalle_por_dia[fecha] = {"cantidad": 0, "monto": 0, "pacientes": []}
        detalle_por_dia[fecha]["cantidad"] += 1
        detalle_por_dia[fecha]["monto"] += pago.get("monto", 0)
        detalle_por_dia[fecha]["pacientes"].append({
            "nombre": pago.get("nombre_paciente", ""),
            "monto": pago.get("monto", 0),
            "tipo_pago": pago.get("tipo_pago", "")
        })

    return jsonify({
        "total_mes": total_mes,
        "pagos_particulares": pagos_particulares,
        "pagos_obra_social": pagos_obra_social,
        "cantidad_pagos_mes": cantidad_pagos_mes,
        "detalle_por_dia": detalle_por_dia,
        "pagos_efectivo": len(pagos_efectivo),
        "pagos_transferencia": len(pagos_transferencia),
        "pagos_obra_social_count": len(pagos_obra_social_list),
        "total_efectivo": total_efectivo,
        "total_transferencia": total_transferencia,
        "total_obra_social": total_obra_social,
    })

@app.route("/api/pagos/exportar-admin", methods=["GET"])
@login_requerido
@rol_requerido("administrador")
def exportar_pagos_csv_admin():
    """Exportar pagos a CSV para administradores (día o mes)."""
    fecha_param = request.args.get("fecha")
    mes = request.args.get("mes")
    if fecha_param:
        filtro_mes = fecha_param[:7]
        pagos = [p for p in cargar_pagos_mes_con_pacientes(filtro_mes) if p.get("fecha") == fecha_param]
    else:
        if not mes:
            mes = datetime.now().strftime("%Y-%m")
        pagos = cargar_pagos_mes_con_pacientes(mes)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Fecha", "DNI", "Paciente", "Monto", "Tipo Pago", "Obra Social", "Observaciones"]) 
    for p in pagos:
        writer.writerow([
            p.get("fecha", ""),
            p.get("dni_paciente", ""),
            p.get("nombre_paciente", ""),
            p.get("monto", 0),
            p.get("tipo_pago", ""),
            p.get("obra_social", ""),
            (p.get("observaciones", "") or "").replace("\n", " ").strip(),
        ])

    csv_data = output.getvalue().encode("utf-8")
    mem = io.BytesIO(csv_data)
    mem.seek(0)

    nombre = f"pagos_{fecha_param}.csv" if fecha_param else f"pagos_{mes}.csv"
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name=nombre)

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

    conn = get_db_connection()
    try:
        cur = conn.cursor()

        # 1) Verificar turno recepcionado
        cur.execute("""
            SELECT estado FROM turnos
            WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
        """, (dni_paciente, fecha, hora))
        
        row = cur.fetchone()
        if not row:
            return jsonify({"error": "Turno no encontrado"}), 404
        
        if (row[0] or "").lower() != "recepcionado":
            return jsonify({"error": "El paciente debe estar recepcionado primero"}), 400
        
        # 2) Verificar paciente
        cur.execute("SELECT nombre, apellido, obra_social FROM pacientes WHERE dni=?", (dni_paciente,))
        p = cur.fetchone()
        if not p:
            return jsonify({"error": "Paciente no encontrado"}), 404
     
        # 3) Permitir múltiples pagos en la misma fecha: eliminar validación de duplicados

        # 4) Insertar pago
        cur.execute("""
            INSERT INTO pagos (dni_paciente, monto, fecha_pago, metodo_pago, obra_social, observaciones, fecha_creacion)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            dni_paciente,
            monto,
            fecha,
            tipo_pago,
            p[2] or "",
            observaciones,
            datetime.now().isoformat(),
        ))

        # 5) Actualizar turno a sala de espera
        cur.execute("""
            UPDATE turnos
            SET estado='sala de espera'
            WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
        """, (dni_paciente, fecha, hora))

        conn.commit()
        return jsonify({"mensaje": "Paciente movido a sala de espera correctamente"})
        
    except Exception as e:
        return jsonify({"error": f"Error al mover a sala de espera: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/turnos/estado", methods=["PUT"])
@login_requerido
@rol_permitido(["medico"])
def actualizar_estado_turno():
    """Actualizar estado de turno (llamado, atendido, ausente)"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Cuerpo inválido; enviar JSON"}), 400
    
    dni_paciente = data.get("dni_paciente")
    fecha = data.get("fecha")
    hora = data.get("hora")
    nuevo_estado = data.get("estado")

    if not all([dni_paciente, fecha, hora, nuevo_estado]):
        return jsonify({"error": "DNI, fecha, hora y estado son requeridos"}), 400

    if nuevo_estado not in ["sin atender", "llamado", "atendido", "ausente"]:
        return jsonify({"error": "Estado inválido. Debe ser: sin atender, llamado, atendido, ausente"}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        
        # Verificar que existe el turno
        cur.execute("""
            SELECT estado FROM turnos 
            WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
        """, (dni_paciente, fecha, hora))
        
        turno = cur.fetchone()
        if not turno:
            return jsonify({"error": "Turno no encontrado"}), 404
        
        # Actualizar estado
        cur.execute("""
            UPDATE turnos 
            SET estado=?
            WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
        """, (nuevo_estado, dni_paciente, fecha, hora))
        
        conn.commit()
        return jsonify({"mensaje": "Estado actualizado correctamente"})
        
    except Exception as e:
        return jsonify({"error": f"Error al actualizar estado: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/turnos/<dni>/<fecha>/<hora>", methods=["PUT"])
@login_requerido
@rol_permitido(["secretaria", "medico"])
def editar_turno(dni, fecha, hora):
    """Editar un turno específico por DNI, fecha y hora"""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Cuerpo inválido; enviar JSON"}), 400
    
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar que existe el turno
        cur.execute("""
            SELECT estado FROM turnos 
            WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
        """, (dni, fecha, hora))
        
        turno = cur.fetchone()
        if not turno:
            return jsonify({"error": "Turno no encontrado"}), 404
        
        # Procesar actualizaciones
        nueva_hora = data.get("nueva_hora")
        nueva_fecha = data.get("nueva_fecha")
        
        if nueva_hora:
            # Verificar que la nueva hora no esté ocupada por otro turno del mismo médico
            cur.execute("""
                SELECT dni_paciente FROM turnos 
                WHERE medico = (SELECT medico FROM turnos WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?)
                AND fecha_turno = ? AND hora_turno = ? 
                AND NOT (dni_paciente = ? AND fecha_turno = ? AND hora_turno = ?)
            """, (dni, fecha, hora, nueva_fecha or fecha, nueva_hora, dni, fecha, hora))
            
            if cur.fetchone():
                return jsonify({"error": "La nueva hora ya está ocupada"}), 400
            
            # Actualizar hora
            cur.execute("""
                UPDATE turnos 
                SET hora_turno = ?
                WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
            """, (nueva_hora, dni, fecha, hora))
        
        if nueva_fecha:
            # Verificar que la nueva fecha/hora no esté ocupada
            fecha_a_verificar = nueva_fecha
            hora_a_verificar = nueva_hora or hora
            
            cur.execute("""
                SELECT dni_paciente FROM turnos 
                WHERE medico = (SELECT medico FROM turnos WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?)
                AND fecha_turno = ? AND hora_turno = ? 
                AND NOT (dni_paciente = ? AND fecha_turno = ? AND hora_turno = ?)
                """, (dni, fecha, hora, fecha_a_verificar, hora_a_verificar, dni, fecha, hora))
            
            if cur.fetchone():
                return jsonify({"error": "La nueva fecha/hora ya está ocupada"}), 400
            
            # Actualizar fecha
            cur.execute("""
                UPDATE turnos 
                SET fecha_turno = ?
                WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
            """, (nueva_fecha, dni, fecha, hora))
        
        conn.commit()
        return jsonify({"mensaje": "Turno actualizado correctamente"})
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Error al actualizar turno: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/turnos/<int:turno_id>", methods=["DELETE"])
@login_requerido
@rol_permitido(["secretaria", "medico", "administrador"])
def eliminar_turno_por_id(turno_id):
    """Eliminar un turno por ID (compatibilidad con agenda.html)"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Verificar existencia
        cur.execute("SELECT id FROM turnos WHERE id = ?", (turno_id,))
        turno = cur.fetchone()
        if not turno:
            return jsonify({"error": "Turno no encontrado"}), 404

        # Eliminar
        cur.execute("DELETE FROM turnos WHERE id = ?", (turno_id,))
        conn.commit()
        return jsonify({"success": True, "mensaje": "Turno eliminado correctamente"})

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Error al eliminar turno: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/api/turnos/<dni>/<fecha>/<hora>", methods=["DELETE"])
@login_requerido
@rol_permitido(["secretaria"])
def eliminar_turno(dni, fecha, hora):
    """Eliminar un turno específico por DNI, fecha y hora"""
    conn = None
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Verificar que existe el turno
        cur.execute("""
            SELECT id FROM turnos 
            WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
        """, (dni, fecha, hora))
        
        turno = cur.fetchone()
        if not turno:
            return jsonify({"error": "Turno no encontrado"}), 404
        
        # Eliminar el turno
        cur.execute("""
            DELETE FROM turnos 
            WHERE dni_paciente=? AND fecha_turno=? AND hora_turno=?
        """, (dni, fecha, hora))
        
        conn.commit()
        return jsonify({
            "success": True,
            "mensaje": "Turno eliminado correctamente"
        })
        
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": f"Error al eliminar turno: {str(e)}"}), 500
    finally:
        if conn:
            conn.close()

@app.route("/historias", methods=["POST"])
@login_requerido
@rol_permitido(["medico"])
def guardar_historia():
    """Guardar una nueva historia clínica"""
    try:
        data = request.get_json()
        print(f"DEBUG - Datos recibidos: {data}")
        
        # Validar campos requeridos
        campos_requeridos = ['dni', 'consulta_medica', 'medico']
        for campo in campos_requeridos:
            if not data.get(campo):
                print(f"ERROR - Campo faltante: {campo}")
                return jsonify({"error": f"El campo '{campo}' es obligatorio"}), 400
        
        conn = get_db_connection()
        c = conn.cursor()
        
        # Verificar si el paciente existe
        c.execute("SELECT * FROM pacientes WHERE dni = ?", (data['dni'],))
        paciente_existente = c.fetchone()
        
        # Si el paciente no existe, crear uno básico
        if not paciente_existente:
            print(f"DEBUG - Paciente con DNI {data['dni']} no existe, creando paciente básico")
            c.execute("""
                INSERT INTO pacientes (dni, nombre, apellido, fecha_nacimiento, obra_social, numero_obra_social, celular)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                data['dni'],
                'Pendiente',  # Nombre temporal
                'Pendiente',  # Apellido temporal
                '',           # Fecha de nacimiento vacía
                '',           # Obra social vacía
                '',           # Número de obra social vacío
                ''            # Celular vacío
            ))
            print(f"DEBUG - Paciente básico creado para DNI {data['dni']}")
        
        # Obtener fecha actual si no viene en los datos
        fecha_consulta = data.get('fecha_consulta')
        if not fecha_consulta:
            fecha_consulta = datetime.now().strftime('%Y-%m-%d')
        
        # Agregar fecha_creacion
        fecha_creacion = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        print(f"DEBUG - Insertando historia: dni={data['dni']}, medico={data['medico']}, fecha_consulta={fecha_consulta}")
        
        # Insertar nueva historia clínica
        c.execute("""
            INSERT INTO historias_clinicas (dni, consulta_medica, medico, fecha_consulta, fecha_creacion)
            VALUES (?, ?, ?, ?, ?)
        """, (
            data['dni'],
            data['consulta_medica'],
            data['medico'],
            fecha_consulta,
            fecha_creacion
        ))
        
        conn.commit()
        conn.close()
        
        print("DEBUG - Historia guardada correctamente")
        return jsonify({"success": True, "mensaje": "Historia clínica guardada correctamente"})
        
    except Exception as e:
        print(f"ERROR al guardar historia: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": f"Error al guardar la historia clínica: {str(e)}"}), 500

@app.route("/historias")
@login_requerido
@rol_permitido(["medico"])
def historias():
    dni = request.args.get('dni')
    if dni:
        return redirect(f"/historia/{dni}")
    return redirect("/historias-gestion")

@app.route("/historia/<dni>")
@login_requerido
@rol_permitido(["medico"])
def historia_clinica(dni):
    return render_template("historia_clinica.html", dni=dni)

@app.route("/historias/<dni>")
@login_requerido
@rol_permitido(["medico"])
def obtener_historia_por_dni(dni):
    """Obtener historias clínicas de un paciente específico por DNI"""
    try:
        conn = get_db_connection()
        c = conn.cursor()
        
        # Obtener todas las historias del paciente
        c.execute("""
            SELECT dni, consulta_medica, medico, fecha_consulta, fecha_creacion
            FROM historias_clinicas 
            WHERE dni = ?
            ORDER BY fecha_consulta DESC
        """, (dni,))
        
        historias = c.fetchall()
        conn.close()
        
        if not historias:
            return jsonify({"error": "No se encontraron historias clínicas para este DNI"}), 404
        
        # Convertir a formato JSON
        historias_json = []
        for historia in historias:
            historias_json.append({
                "dni": historia[0],
                "consulta_medica": historia[1],
                "medico": historia[2],
                "fecha_consulta": historia[3],
                "fecha_creacion": historia[4]
            })
        
        return jsonify(historias_json)
        
    except Exception as e:
        print(f"Error al obtener historias por DNI: {e}")
        return jsonify({"error": "Error al obtener historias clínicas"}), 500

@app.route("/historias-gestion")
@login_requerido
@rol_permitido(["secretaria", "medico", "administrador"])
def gestion_historias():
    return render_template("historias_gestion.html")

@app.route("/api/historias", methods=["GET"])
@login_requerido
@rol_permitido(["medico"])
def obtener_historias():
    """Obtener todas las historias clínicas"""
    try:
        historias = cargar_historias()
        return jsonify(historias)
    except Exception as e:
        print(f"Error al obtener historias: {e}")
        return jsonify({"error": "Error al cargar historias clínicas"}), 500

@app.route("/api/historias/buscar")
@login_requerido
@rol_permitido(["secretaria", "medico", "administrador"])
def buscar_historias():
    try:
        busqueda = request.args.get('busqueda', '').strip()
        pagina = int(request.args.get('pagina', 1))
        por_pagina = int(request.args.get('por_pagina', 10))
        ordenar_por = request.args.get('ordenar_por', 'fecha_consulta')
        orden = request.args.get('orden', 'desc')
        
        # Cargar historias clínicas
        historias = cargar_historias()
        
        # Filtrar por búsqueda si se proporciona
        if busqueda:
            historias_filtradas = []
            for historia in historias:
                # Buscar en DNI, médico, fecha o consulta médica
                if (busqueda.lower() in historia.get('dni', '').lower() or
                    busqueda.lower() in historia.get('medico', '').lower() or
                    busqueda.lower() in historia.get('fecha_consulta', '').lower() or
                    busqueda.lower() in historia.get('consulta_medica', '').lower()):
                    historias_filtradas.append(historia)
            historias = historias_filtradas
        
        # Ordenar
        if ordenar_por == 'fecha_consulta':
            historias.sort(key=lambda x: x.get('fecha_consulta', ''), reverse=(orden == 'desc'))
        elif ordenar_por == 'medico':
            historias.sort(key=lambda x: x.get('medico', ''), reverse=(orden == 'desc'))
        elif ordenar_por == 'dni':
            historias.sort(key=lambda x: x.get('dni', ''), reverse=(orden == 'desc'))
        
        # Paginación
        total = len(historias)
        inicio = (pagina - 1) * por_pagina
        fin = inicio + por_pagina
        historias_pagina = historias[inicio:fin]
        
        # Agrupar por paciente
        pacientes_dict = {}
        for historia in historias_pagina:
            dni = historia.get('dni')
            if dni not in pacientes_dict:
                pacientes_dict[dni] = {
                    'dni': dni,
                    'historias': [],
                    'ultima_consulta': '',
                    'ultima_historia': None
                }
            pacientes_dict[dni]['historias'].append(historia)
        
        # Calcular última consulta y última historia para cada paciente
        pacientes = []
        for dni, paciente_data in pacientes_dict.items():
            # Calcular total de consultas
            paciente_data['total_consultas'] = len(paciente_data['historias'])
            
            if paciente_data['historias']:
                # Ordenar historias por fecha (más reciente primero)
                historias_ordenadas = sorted(paciente_data['historias'], 
                                           key=lambda x: x.get('fecha_consulta', ''), 
                                           reverse=True)
                paciente_data['ultima_consulta'] = historias_ordenadas[0].get('fecha_consulta', '')
                paciente_data['ultima_historia'] = historias_ordenadas[0]
            
            # Obtener datos del paciente desde la base de datos
            try:
                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT nombre, apellido, celular FROM pacientes WHERE dni = ?", (dni,))
                paciente_info = c.fetchone()
                if paciente_info:
                    paciente_data['paciente'] = {
                        'dni': dni,
                        'nombre': paciente_info[0] or '',
                        'apellido': paciente_info[1] or '',
                        'celular': paciente_info[2] or ''
                    }
                else:
                    paciente_data['paciente'] = {
                        'dni': dni,
                        'nombre': 'No encontrado',
                        'apellido': '',
                        'celular': ''
                    }
                conn.close()
            except Exception as e:
                print(f"Error al obtener datos del paciente {dni}: {e}")
                paciente_data['paciente'] = {
                    'dni': dni,
                    'nombre': 'Error',
                    'apellido': '',
                    'celular': ''
                }
            
            pacientes.append(paciente_data)
        
        return jsonify({
            'pacientes': pacientes,
            'total': total,
            'pagina': pagina,
            'por_pagina': por_pagina,
            'total_paginas': (total + por_pagina - 1) // por_pagina
        })
        
    except Exception as e:
        print(f"Error en buscar_historias: {e}")
        return jsonify({'error': 'Error al buscar historias clínicas'}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
