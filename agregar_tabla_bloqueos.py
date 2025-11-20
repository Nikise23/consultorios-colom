#!/usr/bin/env python3
"""
Script para agregar la tabla bloqueos_agenda a la base de datos existente
"""

import sqlite3
import os

def agregar_tabla_bloqueos():
    """Agregar tabla bloqueos_agenda si no existe"""
    
    # Buscar la base de datos
    db_path = 'data/consultorio.db'
    if not os.path.exists(db_path):
        db_path = 'consultorio.db'
        if not os.path.exists(db_path):
            print("❌ No se encontró la base de datos")
            return False
    
    print(f"📁 Base de datos encontrada: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Verificar si la tabla ya existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='bloqueos_agenda'
        """)
        
        if cursor.fetchone():
            print("✅ La tabla 'bloqueos_agenda' ya existe")
            conn.close()
            return True
        
        # Crear la tabla
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bloqueos_agenda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medico TEXT NOT NULL,
                fecha_inicio TEXT NOT NULL,
                fecha_fin TEXT NOT NULL,
                motivo TEXT,
                activo INTEGER DEFAULT 1,
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        print("✅ Tabla 'bloqueos_agenda' creada exitosamente")
        
        # Verificar que se creó correctamente
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='bloqueos_agenda'")
        if cursor.fetchone():
            print("✅ Verificación: La tabla existe y está lista para usar")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error creando la tabla: {e}")
        conn.rollback()
        conn.close()
        return False

if __name__ == "__main__":
    print("🏗️ Agregando tabla bloqueos_agenda...")
    print("-" * 50)
    agregar_tabla_bloqueos()
    print("-" * 50)
    print("✅ Proceso completado")

