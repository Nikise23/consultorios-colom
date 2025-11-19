# 💾 Guía de Backups en Render.com

## 📋 Plan Starter ($7/mes) - ¿Funciona bien?

**Sí, el sistema funcionaría perfectamente con el plan Starter:**

### ✅ Ventajas del Plan Starter

1. **Sistema siempre activo**: No se duerme después de 15 minutos (a diferencia del plan gratuito)
2. **Almacenamiento persistente**: El sistema de archivos persiste entre reinicios
3. **SQLite funciona bien**: Con almacenamiento persistente, SQLite mantiene los datos
4. **Sin límites de tiempo**: Puedes usar el servicio las 24 horas
5. **PostgreSQL incluido**: Si prefieres, puedes usar PostgreSQL (más robusto)

### ⚠️ Consideraciones

- **Reinicios programados**: Render puede reiniciar el servicio ocasionalmente para actualizaciones
- **Backups manuales**: Aunque los datos persisten, es recomendable hacer backups periódicos
- **PostgreSQL es mejor**: Para producción seria, PostgreSQL es más robusto que SQLite

---

## 💾 Cómo Descargar la Base de Datos (Backup)

### Opción 1: Descargar desde Render Dashboard (Recomendado)

#### Para SQLite:

1. **Conectar por SSH a tu servicio:**
   - En Render Dashboard → Tu Web Service → **"Shell"**
   - O usa el botón **"Connect via SSH"**

2. **Navegar y descargar:**
   ```bash
   # Ver contenido
   ls -la
   ls -la data/
   
   # Ver tamaño de la BD
   du -h data/consultorio.db
   
   # La base de datos está en: data/consultorio.db
   ```

3. **Descargar usando SCP (desde tu computadora):**
   ```bash
   # Obtén el comando SSH desde Render Dashboard → Shell → "Connect via SSH"
   # Ejemplo:
   scp render@your-service.onrender.com:/opt/render/project/src/data/consultorio.db ./backup_consultorio_$(date +%Y%m%d).db
   ```

#### Para PostgreSQL:

1. **En Render Dashboard:**
   - Ve a tu base de datos PostgreSQL
   - Click en **"Info"** → Copia la **"Internal Database URL"**

2. **Descargar usando pg_dump (desde tu computadora):**
   ```bash
   # Instalar PostgreSQL client localmente primero
   # Windows: descargar desde postgresql.org
   # Mac: brew install postgresql
   # Linux: sudo apt-get install postgresql-client
   
   # Hacer backup
   pg_dump "postgresql://user:pass@host:port/dbname" > backup_$(date +%Y%m%d).sql
   ```

### Opción 2: Crear Endpoint de Backup (Automático)

Puedes crear un endpoint en tu aplicación para descargar la base de datos:

```python
# Agregar en app.py (proteger con autenticación de administrador)

@app.route("/admin/backup-db")
@login_requerido
@rol_permitido(["administrador"])
def backup_database():
    """Descargar backup de la base de datos"""
    import shutil
    from datetime import datetime
    
    try:
        # Crear copia temporal
        backup_filename = f"consultorio_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        backup_path = f"data/{backup_filename}"
        
        # Copiar base de datos
        shutil.copy("data/consultorio.db", backup_path)
        
        # Enviar como descarga
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=backup_filename,
            mimetype='application/x-sqlite3'
        )
    except Exception as e:
        return f"Error al crear backup: {str(e)}", 500
```

**Uso:**
- Visita: `https://tu-app.onrender.com/admin/backup-db`
- Se descargará automáticamente la base de datos

### Opción 3: Script Automático de Backup

Crear un script que se ejecute periódicamente:

```python
# backup_script.py
import sqlite3
import shutil
from datetime import datetime
import os

def crear_backup():
    """Crear backup de la base de datos"""
    os.makedirs('backups', exist_ok=True)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backups/consultorio_backup_{timestamp}.db'
    
    # Copiar base de datos
    shutil.copy('data/consultorio.db', backup_file)
    
    # Mantener solo los últimos 10 backups
    backups = sorted([f for f in os.listdir('backups') if f.startswith('consultorio_backup_')])
    if len(backups) > 10:
        for old_backup in backups[:-10]:
            os.remove(f'backups/{old_backup}')
    
    print(f"✅ Backup creado: {backup_file}")
    return backup_file

if __name__ == "__main__":
    crear_backup()
```

**Ejecutar periódicamente:**
- Usar un cron job en Render (si está disponible)
- O crear un endpoint que ejecute el script

---

## 🔄 Restaurar desde Backup

### Para SQLite:

```python
# restore_backup.py
import shutil
import sys

def restaurar_backup(backup_file):
    """Restaurar base de datos desde backup"""
    import os
    
    # Hacer backup del actual primero
    if os.path.exists('data/consultorio.db'):
        shutil.copy('data/consultorio.db', f'data/consultorio.db.bak_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
    
    # Restaurar
    shutil.copy(backup_file, 'data/consultorio.db')
    print(f"✅ Base de datos restaurada desde {backup_file}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python restore_backup.py <archivo_backup.db>")
    else:
        restaurar_backup(sys.argv[1])
```

### Para PostgreSQL:

```bash
# Restaurar desde archivo SQL
psql "postgresql://user:pass@host:port/dbname" < backup.sql
```

---

## 📅 Estrategia de Backups Recomendada

### Para Producción:

1. **Backups diarios automáticos:**
   - Usar endpoint `/admin/backup-db` programado
   - O script automático que se ejecute diariamente

2. **Backups antes de cambios importantes:**
   - Antes de actualizar el código
   - Antes de migraciones de base de datos

3. **Almacenar backups externamente:**
   - Descargar backups a tu computadora
   - Subir a Google Drive, Dropbox, o S3
   - Mantener al menos los últimos 30 días

### Script de Backup Automático Mejorado:

```python
# backup_automatico.py
import sqlite3
import shutil
from datetime import datetime
import os
import requests  # Para subir a servicios externos

def crear_backup_completo():
    """Crear backup completo con opción de subir a servicio externo"""
    
    # 1. Crear backup local
    os.makedirs('backups', exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = f'backups/consultorio_backup_{timestamp}.db'
    
    shutil.copy('data/consultorio.db', backup_file)
    print(f"✅ Backup local creado: {backup_file}")
    
    # 2. Verificar integridad
    try:
        conn = sqlite3.connect(backup_file)
        conn.execute("SELECT COUNT(*) FROM usuarios")
        conn.close()
        print("✅ Backup verificado (integridad OK)")
    except Exception as e:
        print(f"❌ Error verificando backup: {e}")
        return None
    
    # 3. Limpiar backups antiguos (mantener últimos 10)
    backups = sorted([f for f in os.listdir('backups') if f.startswith('consultorio_backup_')])
    if len(backups) > 10:
        for old_backup in backups[:-10]:
            os.remove(f'backups/{old_backup}')
            print(f"🗑️ Backup antiguo eliminado: {old_backup}")
    
    return backup_file

if __name__ == "__main__":
    crear_backup_completo()
```

---

## 🔐 Endpoint de Backup Seguro (Recomendado)

Aquí tienes un endpoint completo y seguro para backups:

```python
# Agregar en app.py

@app.route("/admin/backup-db")
@login_requerido
@rol_permitido(["administrador"])
def backup_database():
    """Descargar backup de la base de datos (solo administradores)"""
    import shutil
    from datetime import datetime
    import os
    
    try:
        # Verificar que la BD existe
        if not os.path.exists("data/consultorio.db"):
            return "Base de datos no encontrada", 404
        
        # Crear nombre de backup con timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f"consultorio_backup_{timestamp}.db"
        backup_path = f"data/{backup_filename}"
        
        # Crear copia
        shutil.copy("data/consultorio.db", backup_path)
        
        # Verificar que se copió correctamente
        if not os.path.exists(backup_path):
            return "Error al crear backup", 500
        
        # Enviar como descarga
        return send_file(
            backup_path,
            as_attachment=True,
            download_name=backup_filename,
            mimetype='application/x-sqlite3'
        )
    except Exception as e:
        print(f"Error en backup: {e}")
        import traceback
        traceback.print_exc()
        return f"Error al crear backup: {str(e)}", 500

@app.route("/admin/restore-db", methods=["GET", "POST"])
@login_requerido
@rol_permitido(["administrador"])
def restore_database():
    """Restaurar base de datos desde backup (solo administradores)"""
    if request.method == "POST":
        if 'backup_file' not in request.files:
            return "No se proporcionó archivo", 400
        
        file = request.files['backup_file']
        if file.filename == '':
            return "No se seleccionó archivo", 400
        
        try:
            import shutil
            from datetime import datetime
            
            # Hacer backup del actual
            if os.path.exists("data/consultorio.db"):
                backup_actual = f"data/consultorio_backup_antes_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                shutil.copy("data/consultorio.db", backup_actual)
            
            # Guardar archivo subido
            file.save("data/consultorio.db")
            
            # Verificar integridad
            conn = get_db_connection()
            conn.execute("SELECT COUNT(*) FROM usuarios")
            conn.close()
            
            return "✅ Base de datos restaurada exitosamente"
        except Exception as e:
            return f"Error al restaurar: {str(e)}", 500
    
    return """
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <h2>Restaurar Base de Datos</h2>
        <form method="POST" enctype="multipart/form-data">
            <input type="file" name="backup_file" accept=".db" required>
            <button type="submit">Restaurar</button>
        </form>
        <p style="color: red; margin-top: 20px;">
            ⚠️ Advertencia: Esto reemplazará la base de datos actual.
        </p>
    </body>
    </html>
    """
```

---

## 📊 Comparación: SQLite vs PostgreSQL en Render

| Característica | SQLite (Plan Starter) | PostgreSQL (Plan Starter) |
|----------------|----------------------|---------------------------|
| **Persistencia** | ✅ Sí (con plan Starter) | ✅ Sí |
| **Backups** | Manual (endpoint/script) | Automáticos (planes de pago) |
| **Escalabilidad** | Limitada | Excelente |
| **Concurrencia** | Buena (con WAL) | Excelente |
| **Costo** | Incluido | Incluido en Starter |
| **Complejidad** | Simple | Requiere migración de código |

**Recomendación:**
- **SQLite**: Perfecto para empezar, funciona bien con Starter
- **PostgreSQL**: Mejor para producción seria, más robusto

---

## ✅ Checklist de Backups

- [ ] Plan Starter activado ($7/mes)
- [ ] Endpoint `/admin/backup-db` creado y protegido
- [ ] Backup manual realizado y verificado
- [ ] Estrategia de backups definida (diario/semanal)
- [ ] Backups almacenados externamente (Google Drive, etc.)
- [ ] Proceso de restauración probado
- [ ] Documentación de backups para el equipo

---

## 🆘 Solución de Problemas

### Error: "Permission denied" al descargar

**Solución**: Asegúrate de estar logueado como administrador.

### Error: "Database is locked" durante backup

**Solución**: El sistema está en uso. Intenta en horario de menor tráfico.

### Backup muy grande

**Solución**: 
- Comprimir antes de descargar
- Usar `sqlite3` para exportar solo datos (sin índices)

```bash
sqlite3 data/consultorio.db ".dump" > backup.sql
```

---

**Con el plan Starter, tu sistema funcionará perfectamente y podrás hacer backups fácilmente.** 🎉

