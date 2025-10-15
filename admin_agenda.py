import json
import os
from datetime import datetime, timedelta
import sqlite3
 
DB_PATH = "data/consultorio.db"
 
DIAS = ["LUNES", "MARTES", "MIERCOLES", "JUEVES", "VIERNES"]
 

def cargar_agenda():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("SELECT medico, dia, hora FROM agenda")
        agenda = {}
        for medico, dia, hora in c.fetchall():
            agenda.setdefault(medico, {}).setdefault(dia, []).append(hora)
        for med in agenda:
            for dia in agenda[med]:
                agenda[med][dia] = sorted(agenda[med][dia])
        return agenda
    finally:
        conn.close()
 

def guardar_horarios_medico(medico: str, nombre_dia: str, horas: list[str]):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        with conn:
            c.execute("DELETE FROM agenda WHERE medico=? AND dia=?", (medico, nombre_dia))
            for hora in horas:
                c.execute(
                    "INSERT OR IGNORE INTO agenda (medico, dia, hora) VALUES (?, ?, ?)",
                    (medico, nombre_dia, hora),
                )
    finally:
        conn.close()
 

def input_horarios(dia):
    print(f"\nIngrese los horarios para {dia} separados por coma (ej: 14:05, 14:10, ...), o deje vacío para ninguno:")
    val = input(f"Horarios para {dia}: ").strip()
    return [h.strip() for h in val.split(",") if h.strip()] if val else []
 

def agregar_medico():
    agenda = cargar_agenda()
    nombre = input("Nombre completo del médico a agregar: ").strip()
    if not nombre:
        print("❌ Nombre no puede estar vacío.")
        return
    if nombre in agenda:
        print(f"❌ El médico '{nombre}' ya existe en la agenda.")
        return
    horarios = {}
    for dia in DIAS:
        horas = input_horarios(dia)
        horarios[dia] = horas
        guardar_horarios_medico(nombre, dia, horas)
    print(f"✅ Médico '{nombre}' agregado a la agenda.")
 

def borrar_medico():
    agenda = cargar_agenda()
    nombre = input("Nombre completo del médico a borrar: ").strip()
    if nombre not in agenda:
        print(f"❌ El médico '{nombre}' no existe en la agenda.")
        return
    confirm = input(f"¿Seguro que quieres borrar a '{nombre}'? (s/N): ").strip().lower()
    if confirm == 's':
        conn = sqlite3.connect(DB_PATH)
        try:
            with conn:
                conn.execute("DELETE FROM agenda WHERE medico=?", (nombre,))
            print(f"✅ Médico '{nombre}' borrado de la agenda.")
        finally:
            conn.close()
    else:
        print("Operación cancelada.")
 

def menu():
    while True:
        print("\n=== ADMINISTRACIÓN DE AGENDA ===")
        print("1. Agregar médico y horarios")
        print("2. Borrar médico")
        print("3. Ver agenda actual")
        print("0. Salir")
        op = input("Opción: ").strip()
        if op == '1':
            agregar_medico()
        elif op == '2':
            borrar_medico()
        elif op == '3':
            agenda = cargar_agenda()
            for med, dias in agenda.items():
                print(f"\n{med}:")
                for dia, hs in dias.items():
                    print(f"  {dia}: {', '.join(hs) if hs else '-'}")
        elif op == '0':
            print("¡Hasta luego!")
            break
        else:
            print("Opción inválida.")
 
if __name__ == "__main__":
    menu()