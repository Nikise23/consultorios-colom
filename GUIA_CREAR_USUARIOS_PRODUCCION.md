# 🔐 Guía: Crear Usuarios en Producción (Render)

Si no puedes subir la base de datos con usuarios, aquí tienes **4 opciones** para crear usuarios en producción:

---

## ✅ Opción 1: Endpoint `/setup-admin` (RECOMENDADO)

**La más fácil y segura** - Ya está implementada en el código.

### Pasos:

1. **Asegúrate de que la base de datos esté creada:**
   - Ve a: `https://tu-app.onrender.com/setup-update-db`
   - Click en "Ejecutar Actualización"
   - Esto crea las tablas necesarias

2. **Crear el primer administrador:**
   - Ve a: `https://tu-app.onrender.com/setup-admin`
   - Completa el formulario:
     - **Usuario**: (ej: `admin`)
     - **Contraseña**: (ej: `tu_contraseña_segura`)
     - **Nombre completo**: (opcional)
   - Click en "Crear Administrador"

3. **Iniciar sesión:**
   - Ve a: `https://tu-app.onrender.com/login`
   - Usa las credenciales que acabas de crear

4. **Crear más usuarios:**
   - Una vez logueado como admin, ve a: `/admin-gestion`
   - Usa el formulario "Crear Nuevo Usuario" para crear más usuarios

### ⚠️ IMPORTANTE:
- Este endpoint **solo funciona si NO hay administradores** en el sistema
- **Elimina este endpoint después de crear el primer admin** por seguridad
- Para eliminarlo, comenta o borra la ruta `/setup-admin` en `app.py`

---

## ✅ Opción 2: Usar el Shell de Render

Si tienes acceso al Shell de Render (plan Starter o superior):

### Pasos:

1. **En Render Dashboard:**
   - Ve a tu servicio → Pestaña **"Shell"**
   - Se abrirá una terminal

2. **Ejecutar script de creación:**
   ```bash
   python crear_usuario.py
   ```

3. **Seguir el menú interactivo:**
   - Selecciona opción `1` (Crear nuevo usuario)
   - Ingresa los datos del usuario

### Ventajas:
- Funciona igual que en local
- Puedes crear múltiples usuarios fácilmente

### Desventajas:
- Requiere plan Starter o superior (no funciona en Free)
- Requiere acceso al Shell

---

## ✅ Opción 3: Crear Script SQL Directo

Crear un script Python que ejecutes desde el Shell o como endpoint temporal:

### Crear archivo `crear_admin_inicial.py`:

```python
import sqlite3
from werkzeug.security import generate_password_hash
import os

DB_PATH = os.path.join("data", "consultorio.db")

def crear_admin_inicial():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Verificar si ya existe
    c.execute("SELECT COUNT(*) FROM usuarios WHERE rol = 'administrador'")
    if c.fetchone()[0] > 0:
        print("⚠️ Ya existe un administrador")
        return
    
    # Crear admin
    usuario = "admin"
    contrasena = "cambiar_esta_contraseña"  # ⚠️ CAMBIAR ESTO
    hash_contraseña = generate_password_hash(contrasena)
    
    c.execute("""
        INSERT INTO usuarios (usuario, contrasena, rol, nombre_completo, activo)
        VALUES (?, ?, 'administrador', 'Administrador', 1)
    """, (usuario, hash_contraseña))
    
    conn.commit()
    conn.close()
    print(f"✅ Administrador '{usuario}' creado")
    print(f"⚠️ Contraseña: {contrasena}")
    print("⚠️ CAMBIA LA CONTRASEÑA DESPUÉS DEL PRIMER LOGIN")

if __name__ == "__main__":
    crear_admin_inicial()
```

### Ejecutar:

**Opción A: Desde Shell de Render:**
```bash
python crear_admin_inicial.py
```

**Opción B: Como endpoint temporal:**
Agregar en `app.py`:
```python
@app.route("/setup-crear-admin")
def setup_crear_admin():
    import subprocess
    result = subprocess.run(["python", "crear_admin_inicial.py"], 
                          capture_output=True, text=True)
    return f"<pre>{result.stdout}</pre>"
```

---

## ✅ Opción 4: Usar API desde Postman/curl

Si ya tienes un usuario administrador, puedes crear usuarios vía API:

### Endpoint:
```
POST https://tu-app.onrender.com/api/usuarios
```

### Headers:
```
Content-Type: application/json
Cookie: session=tu_session_cookie
```

### Body (JSON):
```json
{
  "usuario": "nuevo_usuario",
  "contrasena": "contraseña_segura",
  "rol": "medico",
  "especialidad": "Oftalmología"
}
```

### Ejemplo con curl:
```bash
curl -X POST https://tu-app.onrender.com/api/usuarios \
  -H "Content-Type: application/json" \
  -H "Cookie: session=tu_session" \
  -d '{
    "usuario": "medico1",
    "contrasena": "pass123",
    "rol": "medico",
    "especialidad": "Pediatría"
  }'
```

---

## 📋 Resumen de Opciones

| Opción | Dificultad | Requisitos | Recomendado |
|--------|-----------|------------|-------------|
| **1. `/setup-admin`** | ⭐ Fácil | Ninguno | ✅ **SÍ** |
| **2. Shell + `crear_usuario.py`** | ⭐⭐ Media | Plan Starter+ | ✅ Sí |
| **3. Script SQL directo** | ⭐⭐⭐ Avanzada | Shell o endpoint | ⚠️ Solo si otras fallan |
| **4. API REST** | ⭐⭐ Media | Usuario admin existente | ✅ Para usuarios adicionales |

---

## 🎯 Recomendación Final

**Para el primer despliegue:**
1. Usa **Opción 1** (`/setup-admin`) para crear el primer administrador
2. Luego usa el panel `/admin-gestion` para crear más usuarios
3. Elimina el endpoint `/setup-admin` después de usarlo

**Si el endpoint no funciona:**
- Usa **Opción 2** (Shell) si tienes plan Starter
- O crea un script temporal como en **Opción 3**

---

## 🔒 Seguridad

⚠️ **IMPORTANTE:**
- Elimina endpoints temporales (`/setup-admin`, `/setup-update-db`, `/setup-upload-db`) después de usarlos
- Cambia las contraseñas por defecto inmediatamente
- No uses contraseñas débiles
- No compartas las URLs de setup en público

---

## ❓ Preguntas Frecuentes

**P: ¿Puedo usar `/setup-admin` múltiples veces?**
R: No, solo funciona si NO hay administradores. Una vez creado el primero, debes usar `/admin-gestion`.

**P: ¿Qué pasa si olvido la contraseña del admin?**
R: Puedes crear un nuevo script temporal para resetear la contraseña, o usar el Shell de Render.

**P: ¿Puedo crear usuarios sin ser admin?**
R: No, solo los administradores pueden crear usuarios (excepto el primer admin con `/setup-admin`).

