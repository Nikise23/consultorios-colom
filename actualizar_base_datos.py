#!/usr/bin/env python3
"""
Script para actualizar la base de datos con nuevas tablas y cambios
Ejecutar este script después de hacer pull en producción
"""

import sqlite3
import os
import sys

def actualizar_base_datos():
    """Actualizar la base de datos con nuevas tablas"""
    
    # Buscar la base de datos
    db_path = 'data/consultorio.db'
    if not os.path.exists(db_path):
        db_path = 'consultorio.db'
        if not os.path.exists(db_path):
            print("❌ No se encontró la base de datos")
            print("   Buscando en: data/consultorio.db y consultorio.db")
            return False
    
    print(f"📁 Base de datos encontrada: {db_path}")
    print("-" * 60)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cambios_realizados = []
    
    try:
        # Verificar y crear tabla bloqueos_agenda si no existe
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='bloqueos_agenda'
        """)
        
        if not cursor.fetchone():
            print("📋 Creando tabla 'bloqueos_agenda'...")
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
            cambios_realizados.append("✅ Tabla 'bloqueos_agenda' creada")
        else:
            print("✅ Tabla 'bloqueos_agenda' ya existe")
        
        # Verificar y agregar columna 'activo' a usuarios si no existe
        cursor.execute("PRAGMA table_info(usuarios)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        if 'activo' not in columnas:
            print("📋 Agregando columna 'activo' a tabla 'usuarios'...")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN activo INTEGER DEFAULT 1")
            # Actualizar todos los usuarios existentes como activos
            cursor.execute("UPDATE usuarios SET activo = 1 WHERE activo IS NULL")
            cambios_realizados.append("✅ Columna 'activo' agregada a 'usuarios'")
        else:
            print("✅ Columna 'activo' ya existe en 'usuarios'")
        
        # Verificar y agregar columna 'especialidad' a usuarios si no existe
        if 'especialidad' not in columnas:
            print("📋 Agregando columna 'especialidad' a tabla 'usuarios'...")
            cursor.execute("ALTER TABLE usuarios ADD COLUMN especialidad TEXT")
            cambios_realizados.append("✅ Columna 'especialidad' agregada a 'usuarios'")
        else:
            print("✅ Columna 'especialidad' ya existe en 'usuarios'")
        
        # Verificar y agregar columna 'email' a pacientes si no existe
        cursor.execute("PRAGMA table_info(pacientes)")
        columnas_pacientes = [col[1] for col in cursor.fetchall()]
        
        if 'email' not in columnas_pacientes:
            print("📋 Agregando columna 'email' a tabla 'pacientes'...")
            cursor.execute("ALTER TABLE pacientes ADD COLUMN email TEXT")
            cambios_realizados.append("✅ Columna 'email' agregada a 'pacientes'")
        else:
            print("✅ Columna 'email' ya existe en 'pacientes'")
        
        conn.commit()
        
        print("-" * 60)
        if cambios_realizados:
            print("✅ Actualización completada:")
            for cambio in cambios_realizados:
                print(f"   {cambio}")
        else:
            print("✅ La base de datos ya está actualizada")
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Error actualizando la base de datos: {e}")
        conn.rollback()
        conn.close()
        return False
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            conn.close()
        return False

if __name__ == "__main__":
    print("🔄 Actualizando base de datos...")
    print("=" * 60)
    exito = actualizar_base_datos()
    print("=" * 60)
    if exito:
        print("✅ Proceso completado exitosamente")
        sys.exit(0)
    else:
        print("❌ Hubo errores en la actualización")
        sys.exit(1)

