#!/usr/bin/env python3
"""
Script para crear la tabla de historias clínicas en la base de datos
"""

import sqlite3

def crear_tabla_historias_clinicas():
    """Crear la tabla de historias clínicas"""
    
    print("🏗️ Creando tabla de historias clínicas...")
    
    conn = sqlite3.connect('consultorio.db')
    cursor = conn.cursor()
    
    try:
        # Crear la tabla de historias clínicas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historias_clinicas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dni TEXT NOT NULL,
                consulta_medica TEXT NOT NULL,
                fecha_consulta TEXT NOT NULL,
                medico TEXT NOT NULL,
                fecha_creacion TEXT NOT NULL
            )
        """)
        
        conn.commit()
        print("✅ Tabla 'historias_clinicas' creada exitosamente")
        
        # Verificar que la tabla se creó
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='historias_clinicas'")
        if cursor.fetchone():
            print("✅ Verificación: Tabla 'historias_clinicas' existe")
        else:
            print("❌ Error: Tabla 'historias_clinicas' no se creó")
            
    except sqlite3.Error as e:
        print(f"❌ Error creando tabla: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    crear_tabla_historias_clinicas()






