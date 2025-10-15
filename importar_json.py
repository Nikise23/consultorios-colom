import argparse
import json
import os
import shutil
import sqlite3
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple


DB_PATH = os.path.join("data", "consultorio.db")


def backup_database(db_path: str) -> str:
    """Create a timestamped backup copy of the SQLite database file.

    Returns the backup file path.
    """
    if not os.path.exists(db_path):
        return ""
    ts = datetime.now().strftime("%Y%m%d%H%M%S")
    backup_dir = os.path.join("data")
    os.makedirs(backup_dir, exist_ok=True)
    backup_path = os.path.join(backup_dir, f"consultorio_backup_{ts}.db")
    shutil.copy2(db_path, backup_path)
    return backup_path


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def load_json(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        # allow {"items": [...]} or similar
        for v in data.values():
            if isinstance(v, list):
                return v
    raise ValueError(f"Formato JSON no soportado en {path}")


def coalesce(new_value: Any, current_value: Any) -> Any:
    """Prefer non-empty new_value; otherwise keep current_value."""
    if new_value is None:
        return current_value
    if isinstance(new_value, str) and not new_value.strip():
        return current_value
    return new_value


def upsert_pacientes(conn: sqlite3.Connection, items: Iterable[Dict[str, Any]]) -> Tuple[int, int, int]:
    insertados = 0
    actualizados = 0
    omitidos = 0
    cur = conn.cursor()
    for p in items:
        dni = str(p.get("dni", "")).strip()
        if not dni:
            omitidos += 1
            continue
        cur.execute("SELECT nombre, apellido, fecha_nacimiento, obra_social, numero_obra_social, celular FROM pacientes WHERE dni = ?", (dni,))
        row = cur.fetchone()
        nombre = (p.get("nombre") or "").strip()
        apellido = (p.get("apellido") or "").strip()
        fecha_nacimiento = (p.get("fecha_nacimiento") or p.get("fechaNacimiento") or "").strip()
        obra_social = (p.get("obra_social") or p.get("obraSocial") or "").strip()
        numero_obra_social = (p.get("numero_obra_social") or p.get("numeroObraSocial") or "").strip()
        celular = (p.get("celular") or p.get("telefono") or "").strip()
        if row is None:
            cur.execute(
                """
                INSERT INTO pacientes (dni, nombre, apellido, fecha_nacimiento, obra_social, numero_obra_social, celular)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (dni, nombre, apellido, fecha_nacimiento, obra_social, numero_obra_social, celular),
            )
            insertados += 1
        else:
            nombre_db, apellido_db, fn_db, os_db, nos_db, cel_db = row
            nuevo = (
                coalesce(nombre, nombre_db),
                coalesce(apellido, apellido_db),
                coalesce(fecha_nacimiento, fn_db),
                coalesce(obra_social, os_db),
                coalesce(numero_obra_social, nos_db),
                coalesce(celular, cel_db),
                dni,
            )
            if nuevo[:6] != row:
                cur.execute(
                    """
                    UPDATE pacientes
                    SET nombre = ?, apellido = ?, fecha_nacimiento = ?, obra_social = ?, numero_obra_social = ?, celular = ?
                    WHERE dni = ?
                    """,
                    nuevo,
                )
                actualizados += 1
            else:
                omitidos += 1
    return insertados, actualizados, omitidos


def upsert_turnos(conn: sqlite3.Connection, items: Iterable[Dict[str, Any]]) -> Tuple[int, int, int]:
    insertados = 0
    actualizados = 0
    omitidos = 0
    cur = conn.cursor()
    def ensure_patient(dni_val: str):
        cur.execute("SELECT 1 FROM pacientes WHERE dni=?", (dni_val,))
        if cur.fetchone() is None:
            cur.execute(
                """
                INSERT INTO pacientes (dni, nombre, apellido, fecha_nacimiento, obra_social, numero_obra_social, celular)
                VALUES (?, 'Pendiente', 'Pendiente', '', '', '', '')
                """,
                (dni_val,),
            )

    for t in items:
        medico = (t.get("medico") or "").strip()
        fecha = (t.get("fecha") or t.get("fecha_turno") or "").strip()
        hora = (t.get("hora") or t.get("hora_turno") or "").strip()
        dni = str(t.get("dni") or t.get("dni_paciente") or "").strip()
        if not (medico and fecha and hora and dni):
            omitidos += 1
            continue
        cur.execute(
            "SELECT id, estado, tipo_consulta, costo, pagado, observaciones FROM turnos WHERE medico=? AND fecha_turno=? AND hora_turno=?",
            (medico, fecha, hora),
        )
        row = cur.fetchone()
        estado = (t.get("estado") or "").strip() or "sin atender"
        tipo = (t.get("tipo_consulta") or t.get("tipo") or "").strip()
        costo = float(t.get("costo") or t.get("monto") or 0)
        pagado = int(t.get("pagado") or 0)
        obs = (t.get("observaciones") or "").strip()
        if row is None:
            # asegurar paciente
            ensure_patient(dni)
            cur.execute(
                """
                INSERT INTO turnos (medico, hora_turno, fecha_turno, dni_paciente, estado, tipo_consulta, costo, pagado, observaciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (medico, hora, fecha, dni, estado, tipo, costo, pagado, obs),
            )
            insertados += 1
        else:
            _id, estado_db, tipo_db, costo_db, pagado_db, obs_db = row
            nuevos = (coalesce(estado, estado_db), coalesce(tipo, tipo_db), costo if costo else costo_db, pagado if pagado else pagado_db, coalesce(obs, obs_db), _id)
            if nuevos[:5] != (estado_db, tipo_db, costo_db, pagado_db, obs_db):
                cur.execute(
                    "UPDATE turnos SET estado=?, tipo_consulta=?, costo=?, pagado=?, observaciones=? WHERE id=?",
                    nuevos,
                )
                actualizados += 1
            else:
                omitidos += 1
    return insertados, actualizados, omitidos


def upsert_pagos(conn: sqlite3.Connection, items: Iterable[Dict[str, Any]]) -> Tuple[int, int, int]:
    insertados = 0
    actualizados = 0
    omitidos = 0
    cur = conn.cursor()
    def ensure_patient(dni_val: str):
        cur.execute("SELECT 1 FROM pacientes WHERE dni=?", (dni_val,))
        if cur.fetchone() is None:
            cur.execute(
                """
                INSERT INTO pacientes (dni, nombre, apellido, fecha_nacimiento, obra_social, numero_obra_social, celular)
                VALUES (?, 'Pendiente', 'Pendiente', '', '', '', '')
                """,
                (dni_val,),
            )

    for p in items:
        dni = str(p.get("dni_paciente") or p.get("dni") or "").strip()
        fecha = (p.get("fecha") or p.get("fecha_pago") or "").strip()
        monto = float(p.get("monto") or 0)
        metodo = (p.get("metodo_pago") or p.get("tipo_pago") or "").strip() or "efectivo"
        if not (dni and fecha and metodo):
            omitidos += 1
            continue
        cur.execute(
            "SELECT id, obra_social, observaciones FROM pagos WHERE dni_paciente=? AND fecha_pago=? AND metodo_pago=? AND ABS(monto - ?) < 1e-6",
            (dni, fecha, metodo, monto),
        )
        row = cur.fetchone()
        obra_social = (p.get("obra_social") or "").strip()
        observaciones = (p.get("observaciones") or "").strip()
        if row is None:
            # asegurar paciente
            ensure_patient(dni)
            cur.execute(
                """
                INSERT INTO pagos (dni_paciente, monto, fecha_pago, metodo_pago, obra_social, observaciones, fecha_creacion)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (dni, monto, fecha, metodo, obra_social, observaciones, datetime.now().isoformat()),
            )
            insertados += 1
        else:
            _id, os_db, obs_db = row
            nuevos = (coalesce(obra_social, os_db), coalesce(observaciones, obs_db), _id)
            if nuevos[:2] != (os_db, obs_db):
                cur.execute("UPDATE pagos SET obra_social=?, observaciones=? WHERE id=?", nuevos)
                actualizados += 1
            else:
                omitidos += 1
    return insertados, actualizados, omitidos


def upsert_historias(conn: sqlite3.Connection, items: Iterable[Dict[str, Any]]) -> Tuple[int, int, int]:
    insertados = 0
    actualizados = 0
    omitidos = 0
    cur = conn.cursor()
    for h in items:
        dni = str(h.get("dni") or "").strip()
        medico = (h.get("medico") or "").strip()
        fecha = (h.get("fecha_consulta") or h.get("fecha") or "").strip()
        if not (dni and medico and fecha):
            omitidos += 1
            continue
        cur.execute(
            "SELECT consulta_medica FROM historias_clinicas WHERE dni=? AND medico=? AND fecha_consulta=?",
            (dni, medico, fecha),
        )
        row = cur.fetchone()
        consulta = (h.get("consulta_medica") or h.get("consulta") or "").strip()
        if row is None:
            cur.execute(
                """
                INSERT INTO historias_clinicas (dni, consulta_medica, medico, fecha_consulta, fecha_creacion)
                VALUES (?, ?, ?, ?, ?)
                """,
                (dni, consulta, medico, fecha, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
            )
            insertados += 1
        else:
            consulta_db = row[0]
            if consulta and consulta != consulta_db:
                cur.execute(
                    "UPDATE historias_clinicas SET consulta_medica=? WHERE dni=? AND medico=? AND fecha_consulta=?",
                    (consulta, dni, medico, fecha),
                )
                actualizados += 1
            else:
                omitidos += 1
    return insertados, actualizados, omitidos


def _find_json_by_keywords(directory: str, keywords: List[str]) -> Optional[str]:
    try:
        for name in os.listdir(directory):
            low = name.lower()
            if not low.endswith('.json'):
                continue
            if all(k in low for k in keywords):
                return os.path.join(directory, name)
    except FileNotFoundError:
        return None
    return None


def import_dir(conn: sqlite3.Connection, directory: str) -> None:
    summary: List[Tuple[str, Tuple[int, int, int]]] = []
    conn.execute("BEGIN")
    try:
        # pacientes: admite nombres como 'pacientes (1).json'
        path_pac = _find_json_by_keywords(directory, ["paciente"]) or os.path.join(directory, "pacientes.json")
        if os.path.exists(path_pac):
            res = upsert_pacientes(conn, load_json(path_pac))
            summary.append(("pacientes", res))

        # turnos: admite 'turnos (1).json'
        path_tur = _find_json_by_keywords(directory, ["turno"]) or os.path.join(directory, "turnos.json")
        if os.path.exists(path_tur):
            res = upsert_turnos(conn, load_json(path_tur))
            summary.append(("turnos", res))

        # pagos: admite 'pagos (2).json'
        path_pag = _find_json_by_keywords(directory, ["pago"]) or os.path.join(directory, "pagos.json")
        if os.path.exists(path_pag):
            res = upsert_pagos(conn, load_json(path_pag))
            summary.append(("pagos", res))

        # historias: admite 'historias_clinicas (1).json' o 'historias.json'
        path_hist = (
            _find_json_by_keywords(directory, ["historia", "clinica"]) or
            _find_json_by_keywords(directory, ["historia"]) or
            os.path.join(directory, "historias.json")
        )
        if os.path.exists(path_hist):
            res = upsert_historias(conn, load_json(path_hist))
            summary.append(("historias_clinicas", res))

        conn.commit()
    except Exception:
        conn.rollback()
        raise

    print("Resumen de importación (insertados, actualizados, omitidos):")
    for tabla, (ins, upd, skip) in summary:
        print(f"- {tabla}: {ins} insertados, {upd} actualizados, {skip} omitidos")


def main():
    parser = argparse.ArgumentParser(description="Importar JSON a SQLite sin duplicados (upsert)")
    parser.add_argument("--dir", default="import", help="Directorio con JSONs (pacientes.json, turnos.json, pagos.json, historias.json)")
    parser.add_argument("--db", default=DB_PATH, help="Ruta a la base SQLite")
    parser.add_argument("--no-backup", action="store_true", help="No crear backup antes de importar")
    args = parser.parse_args()

    if not args.no_backup:
        backup_path = backup_database(args.db)
        if backup_path:
            print(f"Backup creado: {backup_path}")

    os.makedirs(os.path.dirname(args.db), exist_ok=True)
    conn = connect(args.db)
    try:
        import_dir(conn, args.dir)
    finally:
        conn.close()


if __name__ == "__main__":
    main()


