# 🚀 Guía de Despliegue en Render.com

Esta guía te llevará paso a paso para desplegar el sistema de consultorio médico en Render.com.

---

## 📋 Requisitos Previos

1. **Cuenta en Render.com**: Regístrate en [render.com](https://render.com) (gratis)
2. **Repositorio Git**: Tu código debe estar en GitHub, GitLab o Bitbucket
3. **Archivos necesarios** (ya creados):
   - `Procfile` ✅
   - `requirements.txt` ✅ (actualizado)
   - `runtime.txt` ✅

---

## 🔧 Paso 1: Preparar el Repositorio Git

### 1.1 Inicializar Git (si no lo has hecho)

```bash
git init
git add .
git commit -m "Preparado para despliegue en Render"
```

### 1.2 Subir a GitHub/GitLab/Bitbucket

**Si usas GitHub:**

```bash
# Crear repositorio en GitHub primero, luego:
git remote add origin https://github.com/tu-usuario/tu-repositorio.git
git branch -M main
git push -u origin main
```

**Importante**: Asegúrate de que `.env` esté en `.gitignore` (no subir credenciales)

---

## 🌐 Paso 2: Crear Servicio Web en Render

### 2.1 Acceder a Render Dashboard

1. Ve a [dashboard.render.com](https://dashboard.render.com)
2. Haz clic en **"New +"** → **"Web Service"**

### 2.2 Conectar Repositorio

1. Selecciona tu proveedor (GitHub/GitLab/Bitbucket)
2. Autoriza Render si es necesario
3. Selecciona tu repositorio
4. Haz clic en **"Connect"**

### 2.3 Configurar el Servicio

**Configuración básica:**

- **Name**: `consultorio-medico` (o el nombre que prefieras)
- **Region**: Elige la más cercana (ej: `Oregon (US West)`)
- **Branch**: `main` (o la rama que uses)
- **Root Directory**: (dejar vacío, usa la raíz)
- **Runtime**: `Python 3`
- **Build Command**: 
  ```
  chmod +x build.sh && ./build.sh
  ```
  
  O si prefieres el comando directo:
  ```
  pip install -r requirements.txt && python crear_todas_las_tablas.py && python actualizar_base_datos.py
  ```
- **Start Command**: 
  ```
  gunicorn app:app
  ```

**Configuración avanzada (opcional):**

- **Instance Type**: `Free` (para empezar) o `Starter` ($7/mes)
- **Auto-Deploy**: `Yes` (despliega automáticamente en cada push)

---

## 🔐 Paso 3: Configurar Variables de Entorno

### 3.1 Variables Necesarias

En el dashboard de Render, ve a tu servicio → **"Environment"** → Agrega:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `SECRET_KEY` | `tu-clave-secreta-muy-larga-y-aleatoria` | Clave para sesiones Flask |
| `MAIL_SERVER` | `smtp.gmail.com` | Servidor SMTP |
| `MAIL_PORT` | `587` | Puerto SMTP |
| `MAIL_USE_TLS` | `True` | Usar TLS |
| `MAIL_USERNAME` | `tu_email@gmail.com` | Email para enviar |
| `MAIL_PASSWORD` | `tu_contraseña_de_aplicacion` | Contraseña de aplicación Gmail |
| `MAIL_FROM` | `tu_email@gmail.com` | Email remitente |

**Generar SECRET_KEY:**

```python
import secrets
print(secrets.token_hex(32))
```

**O desde Python:**

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3.2 Configurar Email (Gmail)

1. Ve a tu cuenta de Google: [myaccount.google.com](https://myaccount.google.com)
2. **Seguridad** → **Verificación en 2 pasos** (debe estar activada)
3. **Contraseñas de aplicaciones** → Genera una nueva
4. Usa esa contraseña en `MAIL_PASSWORD`

---

## 💾 Paso 4: Configurar Base de Datos

### ⚠️ IMPORTANTE: SQLite en Render

**Problema**: Render reinicia el sistema periódicamente y el sistema de archivos es efímero. SQLite puede perder datos.

**Soluciones:**

#### Opción A: Usar PostgreSQL (Recomendado)

1. En Render Dashboard → **"New +"** → **"PostgreSQL"**
2. Configura:
   - **Name**: `consultorio-db`
   - **Database**: `consultorio`
   - **User**: (se genera automáticamente)
   - **Region**: Misma que tu web service
3. Copia la **Internal Database URL**
4. En tu Web Service → Environment → Agrega:
   - `DATABASE_URL`: (pega la URL interna)

**Nota**: Esto requiere modificar `app.py` para usar PostgreSQL en lugar de SQLite. Ver sección "Migración a PostgreSQL" más abajo.

#### Opción B: Usar SQLite con Volumen Persistente (Render no lo soporta directamente)

Render no ofrece volúmenes persistentes en el plan gratuito. SQLite funcionará pero **puede perder datos** en reinicios.

**Para desarrollo/pruebas**, puedes usar SQLite pero:
- Los datos pueden perderse
- No recomendado para producción

---

## 🔄 Paso 5: Modificar app.py para Render

### 5.1 Ajustar Ruta de Base de Datos

Render usa un sistema de archivos efímero. Necesitamos asegurar que la carpeta `data/` exista:

```python
# Al inicio de app.py, después de los imports
import os

# Crear directorio data si no existe
os.makedirs('data', exist_ok=True)
```

### 5.2 Ajustar Puerto

Render asigna el puerto automáticamente. Gunicorn ya lo maneja, pero verifica:

```python
# Al final de app.py
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
```

---

## 🚀 Paso 6: Desplegar

### 6.1 Primer Despliegue

1. En Render Dashboard, haz clic en **"Create Web Service"**
2. Render comenzará a construir y desplegar
3. Observa los logs en tiempo real
4. Espera a que termine (5-10 minutos la primera vez)

### 6.2 Verificar Despliegue

1. Una vez completado, Render te dará una URL: `https://tu-app.onrender.com`
2. Visita la URL
3. Deberías ver la página pública de inicio

### 6.3 Crear Usuario Administrador

**Problema**: No puedes ejecutar `crear_usuario.py` directamente en Render.

**Solución**: Crear un endpoint temporal para crear el primer usuario:

```python
# Agregar temporalmente en app.py (después del despliegue, eliminar o proteger)

@app.route("/setup-admin", methods=["GET", "POST"])
def setup_admin():
    """Endpoint temporal para crear primer administrador"""
    if request.method == "POST":
        usuario = request.form.get("usuario")
        contrasena = request.form.get("contrasena")
        
        # Verificar si ya existe admin
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'administrador'")
        if c.fetchone()[0] > 0:
            return "Ya existe un administrador. Elimina este endpoint por seguridad."
        
        # Crear admin
        from werkzeug.security import generate_password_hash
        hash_contraseña = generate_password_hash(contrasena)
        c.execute("""
            INSERT INTO usuarios (usuario, contrasena, rol, nombre_completo, activo)
            VALUES (?, ?, 'administrador', ?, 1)
        """, (usuario, hash_contraseña, usuario))
        conn.commit()
        conn.close()
        
        return "Administrador creado. Elimina este endpoint ahora."
    
    return """
    <form method="POST">
        <input name="usuario" placeholder="Usuario" required>
        <input type="password" name="contrasena" placeholder="Contraseña" required>
        <button type="submit">Crear Admin</button>
    </form>
    """
```

**⚠️ IMPORTANTE**: Elimina este endpoint después de crear el admin por seguridad.

---

## 📝 Paso 7: Verificar Funcionamiento

### 7.1 Checklist

- [ ] La página pública carga correctamente
- [ ] El login funciona
- [ ] Puedes crear usuarios
- [ ] Los turnos se guardan
- [ ] Los emails se envían (verificar logs)
- [ ] La base de datos persiste datos

### 7.2 Ver Logs

En Render Dashboard → Tu servicio → **"Logs"**

Aquí verás:
- Errores de la aplicación
- Logs de email
- Debug información

---

## 🔧 Solución de Problemas Comunes

### Error: "Module not found"

**Solución**: Verifica que `requirements.txt` tenga todas las dependencias.

```bash
# Localmente, prueba:
pip install -r requirements.txt
python app.py
```

### Error: "Database is locked"

**Solución**: SQLite en Render puede tener problemas. Considera PostgreSQL.

### Error: "Port already in use"

**Solución**: Render asigna el puerto automáticamente. No uses `app.run()` en producción, usa Gunicorn (ya configurado en Procfile).

### Error: "No such file or directory: data/consultorio.db"

**Solución**: Asegúrate de que `crear_todas_las_tablas.py` se ejecute en el build command.

### Emails no se envían

**Solución**:
1. Verifica variables de entorno
2. Usa "Contraseña de aplicación" de Gmail (no tu contraseña normal)
3. Revisa logs en Render

### La aplicación se reinicia y pierde datos

**Solución**: Esto es normal con SQLite en Render. **Migra a PostgreSQL** (ver abajo).

---

## 🗄️ Migración a PostgreSQL (Opcional pero Recomendado)

Si quieres usar PostgreSQL en lugar de SQLite:

### 1. Instalar psycopg2

Agrega a `requirements.txt`:
```
psycopg2-binary==2.9.9
```

### 2. Modificar `get_db_connection()` en `app.py`

```python
import os
import psycopg2
from urllib.parse import urlparse

def get_db_connection():
    """Obtener conexión a PostgreSQL o SQLite según disponibilidad"""
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # PostgreSQL en Render
        result = urlparse(database_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        return conn
    else:
        # SQLite local
        os.makedirs('data', exist_ok=True)
        conn = sqlite3.connect("data/consultorio.db", timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn
```

### 3. Adaptar Queries SQL

PostgreSQL usa sintaxis ligeramente diferente:
- `TEXT` → `VARCHAR` o `TEXT`
- `INTEGER` → `INTEGER` o `SERIAL`
- `REAL` → `REAL` o `DECIMAL`
- `CURRENT_TIMESTAMP` → `NOW()`

**Nota**: La mayoría de queries SQLite funcionan en PostgreSQL sin cambios.

### 4. Crear Tablas en PostgreSQL

Modifica `crear_todas_las_tablas.py` para detectar el tipo de BD:

```python
import os
import psycopg2
from urllib.parse import urlparse

def crear_todas_las_tablas():
    database_url = os.environ.get('DATABASE_URL')
    
    if database_url:
        # PostgreSQL
        result = urlparse(database_url)
        conn = psycopg2.connect(
            database=result.path[1:],
            user=result.username,
            password=result.password,
            host=result.hostname,
            port=result.port
        )
        # Usar sintaxis PostgreSQL
    else:
        # SQLite
        conn = sqlite3.connect('data/consultorio.db')
        # Usar sintaxis SQLite
```

---

## 📊 Monitoreo y Mantenimiento

### Ver Estadísticas

Render Dashboard → Tu servicio → **"Metrics"**

Aquí verás:
- CPU usage
- Memory usage
- Request count
- Response times

### Actualizar la Aplicación

1. Haz cambios en tu código
2. Haz commit y push a GitHub
3. Render detecta el cambio y despliega automáticamente (si Auto-Deploy está activado)

### Backups

**Para SQLite**: No hay backups automáticos en Render. Considera:
- Exportar datos periódicamente
- Usar PostgreSQL (tiene backups automáticos en planes de pago)

**Para PostgreSQL**: Render hace backups automáticos en planes de pago.

---

## 💰 Costos

### Plan Gratuito

- **Web Service**: Gratis (se duerme después de 15 min de inactividad)
- **PostgreSQL**: No disponible gratis (mínimo $7/mes)
- **Límites**: 750 horas/mes de CPU

### Plan Starter ($7/mes)

- **Web Service**: Siempre activo
- **PostgreSQL**: Incluido
- **Sin límites de tiempo**

---

## ✅ Checklist Final

Antes de considerar el despliegue completo:

- [ ] Código en repositorio Git
- [ ] `Procfile` creado
- [ ] `requirements.txt` actualizado
- [ ] Variables de entorno configuradas
- [ ] Base de datos configurada (SQLite o PostgreSQL)
- [ ] Primer administrador creado
- [ ] Emails funcionando
- [ ] Endpoint temporal `/setup-admin` eliminado (si se usó)
- [ ] Pruebas realizadas
- [ ] Logs revisados

---

## 🆘 Soporte

Si tienes problemas:

1. **Revisa los logs** en Render Dashboard
2. **Verifica variables de entorno**
3. **Prueba localmente** primero
4. **Consulta la documentación de Render**: [render.com/docs](https://render.com/docs)

---

## 📚 Recursos Adicionales

- [Documentación de Render](https://render.com/docs)
- [Guía de Flask en Render](https://render.com/docs/deploy-flask)
- [Guía de PostgreSQL en Render](https://render.com/docs/databases)

---

**¡Listo!** Tu sistema debería estar funcionando en Render.com 🎉

**URL de tu aplicación**: `https://tu-app.onrender.com`

