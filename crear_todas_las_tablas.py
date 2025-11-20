#!/usr/bin/env python3
"""
Script para crear todas las tablas del sistema de consultorio
"""

import sqlite3

def crear_todas_las_tablas():
    """Crear todas las tablas del sistema"""
    
    print("🏗️ Creando todas las tablas del sistema...")
    
    conn = sqlite3.connect('consultorio.db')
    cursor = conn.cursor()
    
    try:
        # Tabla de usuarios
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT UNIQUE NOT NULL,
                contrasena TEXT NOT NULL,
                rol TEXT NOT NULL,
                nombre_completo TEXT,
                email TEXT,
                telefono TEXT,
                especialidad TEXT,
                activo INTEGER DEFAULT 1,
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Tabla 'usuarios' creada")
        
        # Tabla de pacientes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pacientes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dni TEXT UNIQUE NOT NULL,
                nombre TEXT NOT NULL,
                apellido TEXT NOT NULL,
                fecha_nacimiento TEXT,
                celular TEXT,
                email TEXT,
                direccion TEXT,
                ciudad TEXT,
                provincia TEXT,
                codigo_postal TEXT,
                obra_social TEXT,
                numero_obra_social TEXT,
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Tabla 'pacientes' creada")
        
        # Tabla de turnos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS turnos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dni_paciente TEXT NOT NULL,
                medico TEXT NOT NULL,
                fecha_turno TEXT NOT NULL,
                hora_turno TEXT NOT NULL,
                estado TEXT DEFAULT 'sin atender',
                tipo_consulta TEXT,
                costo REAL DEFAULT 0,
                pagado INTEGER DEFAULT 0,
                observaciones TEXT,
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dni_paciente) REFERENCES pacientes (dni)
            )
        """)
        print("✅ Tabla 'turnos' creada")
        
        # Tabla de pagos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pagos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dni_paciente TEXT NOT NULL,
                fecha_pago TEXT NOT NULL,
                monto REAL NOT NULL,
                metodo_pago TEXT DEFAULT 'efectivo',
                obra_social TEXT,
                observaciones TEXT,
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (dni_paciente) REFERENCES pacientes (dni)
            )
        """)
        print("✅ Tabla 'pagos' creada")
        
        # Tabla de agenda
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agenda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medico TEXT NOT NULL,
                dia_semana TEXT NOT NULL,
                horario TEXT NOT NULL,
                activo INTEGER DEFAULT 1,
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(medico, dia_semana, horario)
            )
        """)
        print("✅ Tabla 'agenda' creada")
        
        # Tabla de historias clínicas (ya existe)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historias_clinicas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dni TEXT NOT NULL,
                consulta_medica TEXT NOT NULL,
                fecha_consulta TEXT NOT NULL,
                medico TEXT NOT NULL,
                fecha_creacion TEXT NOT NULL,
                FOREIGN KEY (dni) REFERENCES pacientes (dni)
            )
        """)
        print("✅ Tabla 'historias_clinicas' verificada")
        
        # Tabla de bloqueos de agenda (vacaciones, etc.)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bloqueos_agenda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                medico TEXT NOT NULL,
                fecha_inicio TEXT NOT NULL,
                fecha_fin TEXT NOT NULL,
                motivo TEXT,
                activo INTEGER DEFAULT 1,
                fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (medico) REFERENCES usuarios(usuario)
            )
        """)
        print("✅ Tabla 'bloqueos_agenda' creada")
        
        conn.commit()
        print("\n🎉 Todas las tablas creadas exitosamente!")
        
        # Verificar todas las tablas
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
        tablas = cursor.fetchall()
        print(f"\n📋 Tablas creadas: {len(tablas)}")
        for tabla in tablas:
            print(f"   📄 {tabla[0]}")
            
    except sqlite3.Error as e:
        print(f"❌ Error creando tablas: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    crear_todas_las_tablas()






