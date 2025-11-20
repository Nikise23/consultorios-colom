# 📥 Guía: Descargar Base de Datos de Producción

Esta guía te explica cómo descargar la base de datos de producción (Render) para trabajar localmente con datos reales.

---

## 🔐 Método 1: Usando el Endpoint de Backup (Recomendado)

### Paso 1: Acceder al Endpoint

1. Inicia sesión en tu aplicación en producción como **administrador**
2. Ve a: `https://tu-app.onrender.com/admin/backup-db`
3. Se descargará automáticamente el archivo `consultorio_backup_YYYYMMDD_HHMMSS.db`

### Paso 2: Reemplazar Base de Datos Local

1. **Hacer backup de tu BD local** (por si acaso):
   ```bash
   # En Windows PowerShell
   Copy-Item data\consultorio.db data\consultorio.db.backup
   
   # O en Git Bash/Linux
   cp data/consultorio.db data/consultorio.db.backup
   ```

2. **Reemplazar con la BD de producción**:
   ```bash
   # Renombrar el archivo descargado
   # Si descargaste: consultorio_backup_20241119_225000.db
   # Renómbralo a: consultorio.db
   
   # En Windows PowerShell
   Move-Item consultorio_backup_20241119_225000.db data\consultorio.db -Force
   
   # O en Git Bash/Linux
   mv consultorio_backup_20241119_225000.db data/consultorio.db
   ```

3. **Verificar que funciona**:
   ```bash
   python -c "import sqlite3; conn = sqlite3.connect('data/consultorio.db'); print('✅ BD conectada correctamente')"
   ```

---

## 🔧 Método 2: Usando SSH (Si tienes acceso)

### Paso 1: Conectar por SSH

1. En Render.com, ve a tu servicio
2. Abre la pestaña **"Shell"** o configura SSH
3. O desde tu terminal local:
   ```bash
   ssh tu-usuario@tu-servidor-render
   ```

### Paso 2: Localizar y Descargar la BD

```bash
# En el servidor de Render
cd /opt/render/project/src  # o la ruta donde está tu proyecto
ls -la data/  # verificar que existe consultorio.db

# Opción A: Usar scp desde tu máquina local
# (desde tu terminal local, NO en el servidor)
scp tu-usuario@tu-servidor:/opt/render/project/src/data/consultorio.db ./data/consultorio.db

# Opción B: Crear un archivo comprimido y descargarlo
# (en el servidor)
tar -czf consultorio_backup.tar.gz data/consultorio.db
# Luego descargar el .tar.gz por el método que prefieras
```

---

## ⚠️ IMPORTANTE: Precauciones

### 1. **NO subir la BD a Git**

La base de datos está en `.gitignore`, pero verifica:

```bash
git status
# NO debería aparecer data/consultorio.db en los cambios
```

### 2. **Hacer Backup Antes de Reemplazar**

Siempre guarda una copia de tu BD local antes de reemplazarla:

```bash
# Windows PowerShell
Copy-Item data\consultorio.db data\consultorio_local_backup_$(Get-Date -Format 'yyyyMMdd').db

# Linux/Mac
cp data/consultorio.db "data/consultorio_local_backup_$(date +%Y%m%d).db"
```

### 3. **Variables de Entorno**

Cuando trabajes con la BD de producción localmente, asegúrate de:
- Usar las mismas variables de entorno (o al menos las necesarias)
- No ejecutar scripts que modifiquen datos de producción accidentalmente

### 4. **Sincronizar Cambios de Estructura**

Si haces cambios en la estructura de la BD localmente:
1. Ejecuta `python actualizar_base_datos.py` localmente
2. Cuando subas a producción, el script se ejecutará automáticamente
3. **NO subas la BD modificada**, solo el código

---

## 🔄 Flujo Completo Recomendado

### Para trabajar con datos de producción:

1. **Descargar BD de producción**:
   - Ve a `/admin/backup-db` en producción
   - Descarga el archivo

2. **Backup de BD local**:
   ```bash
   Copy-Item data\consultorio.db data\consultorio_local_backup.db
   ```

3. **Reemplazar BD local**:
   ```bash
   Move-Item consultorio_backup_*.db data\consultorio.db -Force
   ```

4. **Trabajar localmente** con los datos reales

5. **Al terminar** (opcional, restaurar BD local):
   ```bash
   Move-Item data\consultorio_local_backup.db data\consultorio.db -Force
   ```

---

## 🚨 Problemas Comunes

### Error: "database is locked"
- Cierra todas las conexiones a la BD
- Reinicia tu aplicación Flask local
- Espera unos segundos y vuelve a intentar

### Error: "no such table"
- Ejecuta `python actualizar_base_datos.py` para actualizar la estructura
- O ejecuta `python crear_todas_las_tablas.py`

### La BD descargada no tiene los últimos datos
- Los backups se generan en el momento de la descarga
- Si necesitas datos más recientes, descarga nuevamente

---

## 📝 Notas Finales

- **Frecuencia**: Descarga la BD solo cuando necesites trabajar con datos reales
- **Seguridad**: La BD contiene datos sensibles, mantenla segura
- **Tamaño**: Si la BD es muy grande, considera usar solo una muestra de datos para desarrollo
- **Sincronización**: Los cambios que hagas localmente NO se reflejan automáticamente en producción

