from flask import Flask, request, jsonify
import sqlite3

app = Flask(__name__)

HORARIOS_VALIDOS = [f"{h:02d}:{m:02d}" for h in range(9, 19+1) for m in (0, 30)]
DIAS_VALIDOS = ["lunes", "martes", "miércoles", "jueves", "viernes"]

DB_PATH = "data/consultorio.db"

def cargar_agenda():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT medico, dia, hora FROM agenda")
        agenda = {}
        for medico, dia, hora in c.fetchall():
            agenda.setdefault(medico, {}).setdefault(dia, []).append(hora)
        # ordenar horas
        for med in agenda:
            for dia in agenda[med]:
                agenda[med][dia] = sorted(agenda[med][dia])
        return agenda
    finally:
        conn.close()

def guardar_agenda_para_dia(medico: str, dia: str, horas: list[str]):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        with conn:
            c.execute("DELETE FROM agenda WHERE medico=? AND dia=?", (medico, dia))
            for hora in horas:
                c.execute(
                    "INSERT OR IGNORE INTO agenda (medico, dia, hora) VALUES (?, ?, ?)",
                    (medico, dia, hora),
                )
    finally:
        conn.close()

@app.route("/agenda", methods=["GET"])
def ver_agenda_completa():
    return jsonify(cargar_agenda())

@app.route("/agenda/<medico>", methods=["GET"])
def ver_agenda_medico(medico):
    agenda = cargar_agenda()
    if medico not in agenda:
        return jsonify({"error": "Médico no encontrado"}), 404
    return jsonify(agenda[medico])

@app.route("/agenda/<medico>/<dia>", methods=["PUT"])
def actualizar_dia_agenda(medico, dia):
    datos = request.json  # Se espera una lista de horarios: ["09:00", "10:30", ...]
    if dia not in DIAS_VALIDOS:
        return jsonify({"error": "Día inválido. Solo de lunes a viernes"}), 400
    if not isinstance(datos, list) or not all(isinstance(h, str) for h in datos):
        return jsonify({"error": "Formato inválido. Enviar lista de strings (horarios)"}), 400
    if not all(hora in HORARIOS_VALIDOS for hora in datos):
        return jsonify({"error": "Uno o más horarios no están permitidos (09:00 a 19:00 cada 30 minutos)"}), 400

    agenda = cargar_agenda()
    if medico not in agenda:
        # permitir crear si no existe aún
        agenda[medico] = {}

    guardar_agenda_para_dia(medico, dia, datos)
    return jsonify({"mensaje": f"Agenda actualizada para {medico} el día {dia}"}), 200

