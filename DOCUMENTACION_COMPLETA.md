# 📚 Documentación Completa del Sistema de Consultorio Médico

## 📋 Índice

1. [Introducción](#introducción)
2. [Estructura del Proyecto](#estructura-del-proyecto)
3. [Base de Datos](#base-de-datos)
4. [Configuración Inicial](#configuración-inicial)
5. [Arquitectura del Sistema](#arquitectura-del-sistema)
6. [Rutas y Endpoints](#rutas-y-endpoints)
7. [Templates y Frontend](#templates-y-frontend)
8. [Funcionalidades Principales](#funcionalidades-principales)
9. [Flujos de Trabajo](#flujos-de-trabajo)
10. [Configuración de Email](#configuración-de-email)
11. [Scripts Auxiliares](#scripts-auxiliares)
12. [Guía de Desarrollo](#guía-de-desarrollo)
13. [Solución de Problemas](#solución-de-problemas)

---

## 🎯 Introducción

Este es un sistema completo de gestión de consultorio médico desarrollado en **Flask (Python)** con **SQLite** como base de datos. El sistema permite gestionar usuarios, pacientes, turnos, historias clínicas, pagos y agenda médica.

### Tecnologías Utilizadas

- **Backend**: Python 3.11, Flask
- **Base de Datos**: SQLite (archivo `data/consultorio.db`)
- **Frontend**: HTML5, CSS3, JavaScript, Bootstrap 5.3.3
- **Templating**: Jinja2
- **Email**: SMTP (Gmail)
- **PDF**: WeasyPrint (para historias clínicas)
- **Zona Horaria**: pytz (Argentina UTC-3)

---

## 📁 Estructura del Proyecto

```
consultorio-cb/
│
├── app.py                          # Aplicación Flask principal (todas las rutas y lógica)
├── .env                            # Variables de entorno (email, etc.) - NO COMMITEAR
├── requirements.txt                # Dependencias Python
├── README.md                       # Documentación básica
├── DOCUMENTACION_COMPLETA.md       # Este archivo
│
├── data/                           # Base de datos y backups
│   ├── consultorio.db              # Base de datos principal SQLite
│   ├── consultorio.db-shm          # Archivo compartido de memoria (WAL)
│   ├── consultorio.db-wal          # Write-Ahead Log (WAL)
│   └── consultorio_backup_*.db      # Backups automáticos
│
├── templates/                      # Plantillas HTML (Jinja2)
│   ├── inicio_publico.html         # Página pública de inicio
│   ├── reserva_turno.html          # Formulario público de reserva
│   ├── login.html                  # Página de login
│   ├── index.html                  # Panel principal (médico/secretaria)
│   ├── secretaria.html             # Panel de secretaria
│   ├── administrador.html          # Panel de administrador
│   ├── pacientes.html              # Gestión de pacientes
│   ├── pacientes_turnos.html      # Pacientes con turnos
│   ├── agenda.html                 # Gestión de agenda
│   ├── turnos_medico.html          # Turnos del médico
│   ├── historia_clinica.html       # Vista de historia clínica
│   ├── historias_gestion.html      # Gestión de historias
│   ├── calendario.html             # Vista de calendario
│   └── turnos_recepcionados.html  # Turnos recepcionados
│
├── static/                         # Archivos estáticos
│   └── images/
│       └── 1741704862_logo.png     # Logo del consultorio
│
└── Scripts Auxiliares/
    ├── crear_todas_las_tablas.py   # Crear estructura de BD
    ├── crear_usuario.py            # Crear usuarios desde consola
    ├── agregar_especialidad_medicos.py  # Migración: agregar especialidad
    ├── crear_tabla_historias_clinicas.py  # Crear tabla historias
    ├── importar_json.py            # Importar datos desde JSON
    ├── limpiar_turnos.py           # Limpiar turnos antiguos
    ├── probar_email.py             # Probar envío de emails
    ├── agenda.py                   # API HTTP para agenda
    └── admin_agenda.py             # Admin de agenda desde consola
```

---

## 🗄️ Base de Datos

### Ubicación
- **Archivo**: `data/consultorio.db`
- **Tipo**: SQLite 3
- **Modo**: WAL (Write-Ahead Logging) para mejor concurrencia

### Esquema de Tablas

#### 1. Tabla: `usuarios`
Almacena todos los usuarios del sistema (médicos, secretarias, administradores).

```sql
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE NOT NULL,           -- Nombre de usuario (login)
    contrasena TEXT NOT NULL,                -- Hash de contraseña (Werkzeug)
    rol TEXT NOT NULL,                       -- 'medico', 'secretaria', 'administrador'
    nombre_completo TEXT,                    -- Nombre completo del usuario
    email TEXT,                              -- Email del usuario
    telefono TEXT,                           -- Teléfono de contacto
    especialidad TEXT,                       -- Especialidad médica (solo para médicos)
    activo INTEGER DEFAULT 1,                 -- 1 = activo, 0 = inactivo
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
)
```

**Campos importantes:**
- `especialidad`: Solo se usa para médicos (ej: "Oftalmología", "Traumatología", "Pediatría")
- `rol`: Define permisos y vistas accesibles
- `contrasena`: Hash bcrypt generado con `werkzeug.security.generate_password_hash()`

#### 2. Tabla: `pacientes`
Información completa de los pacientes.

```sql
CREATE TABLE pacientes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dni TEXT UNIQUE NOT NULL,                -- DNI (clave primaria lógica)
    nombre TEXT NOT NULL,
    apellido TEXT NOT NULL,
    fecha_nacimiento TEXT,                    -- Formato: YYYY-MM-DD
    celular TEXT,
    email TEXT,                              -- Para confirmaciones de turno
    direccion TEXT,
    ciudad TEXT,
    provincia TEXT,
    codigo_postal TEXT,
    obra_social TEXT,                        -- Nombre de la obra social
    numero_obra_social TEXT,                 -- Número de afiliado
    registro_rapido INTEGER DEFAULT 0,      -- 1 = registro rápido (datos incompletos)
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
)
```

**Nota**: `registro_rapido = 1` indica que el paciente se registró desde el formulario público con solo DNI y email, y necesita completar sus datos.

#### 3. Tabla: `turnos`
Gestión de turnos médicos.

```sql
CREATE TABLE turnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dni_paciente TEXT NOT NULL,              -- FK a pacientes.dni
    medico TEXT NOT NULL,                     -- FK a usuarios.usuario
    fecha_turno TEXT NOT NULL,                -- Formato: YYYY-MM-DD
    hora_turno TEXT NOT NULL,                 -- Formato: HH:MM
    estado TEXT DEFAULT 'sin atender',        -- Estados: sin atender, recepcionado, sala de espera, llamado, atendido, ausente
    tipo_consulta TEXT,                       -- Tipo de consulta
    costo REAL DEFAULT 0,                     -- Costo de la consulta
    pagado INTEGER DEFAULT 0,                 -- 0 = no pagado, 1 = pagado
    observaciones TEXT,
    hora_recepcion TEXT,                      -- Hora en que fue recepcionado
    hora_sala_espera TEXT,                    -- Hora en que entró a sala de espera
    hora_llamado TEXT,                        -- Hora en que fue llamado
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(medico, fecha_turno, hora_turno, dni_paciente)
)
```

**Estados del turno:**
- `sin atender`: Turno reservado pero paciente aún no llegó
- `recepcionado`: Paciente llegó y fue registrado
- `sala de espera`: Paciente en sala de espera
- `llamado`: Médico llamó al paciente
- `atendido`: Consulta completada
- `ausente`: Paciente no se presentó

#### 4. Tabla: `agenda`
Horarios disponibles por médico y día de la semana.

```sql
CREATE TABLE agenda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medico TEXT NOT NULL,                     -- FK a usuarios.usuario
    dia_semana TEXT NOT NULL,                 -- LUNES, MARTES, MIERCOLES, JUEVES, VIERNES, SABADO, DOMINGO
    horario TEXT NOT NULL,                    -- Formato: HH:MM
    activo INTEGER DEFAULT 1,                 -- 1 = activo, 0 = inactivo
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(medico, dia_semana, horario)
)
```

**Días de la semana**: Deben estar en MAYÚSCULAS (LUNES, MARTES, MIERCOLES, etc.)

#### 5. Tabla: `pagos`
Registro de pagos realizados.

```sql
CREATE TABLE pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dni_paciente TEXT NOT NULL,              -- FK a pacientes.dni
    nombre_paciente TEXT,                     -- Nombre completo (denormalizado)
    monto REAL NOT NULL,
    fecha_pago TEXT NOT NULL,                 -- Formato: YYYY-MM-DD
    metodo_pago TEXT DEFAULT 'efectivo',     -- efectivo, transferencia, obra_social
    obra_social TEXT,                         -- Si método = obra_social
    observaciones TEXT,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
)
```

#### 6. Tabla: `historias_clinicas`
Historias clínicas de los pacientes.

```sql
CREATE TABLE historias_clinicas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dni TEXT NOT NULL,                        -- FK a pacientes.dni
    consulta_medica TEXT NOT NULL,           -- Contenido de la consulta
    medico TEXT NOT NULL,                     -- FK a usuarios.usuario
    fecha_consulta TEXT NOT NULL,             -- Formato: YYYY-MM-DD
    fecha_creacion TEXT NOT NULL,             -- Timestamp de creación
    FOREIGN KEY (dni) REFERENCES pacientes (dni)
)
```

**Nota**: La especialidad del médico se obtiene de `usuarios.especialidad` mediante JOIN.

---

## ⚙️ Configuración Inicial

### 1. Instalación de Dependencias

```bash
pip install -r requirements.txt
```

**Dependencias principales:**
- `flask`: Framework web
- `werkzeug`: Utilidades (hash de contraseñas)
- `pytz`: Zona horaria
- `python-dotenv`: Variables de entorno
- `weasyprint`: Generación de PDFs

### 2. Crear Base de Datos

```bash
python crear_todas_las_tablas.py
```

Esto crea todas las tablas necesarias en `data/consultorio.db`.

### 3. Crear Usuario Administrador

```bash
python crear_usuario.py
```

Seguir las instrucciones para crear el primer usuario (recomendado: administrador).

### 4. Configurar Email (Opcional)

Crear archivo `.env` en la raíz del proyecto:

```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_email@gmail.com
MAIL_PASSWORD=tu_contraseña_de_aplicacion
MAIL_FROM=tu_email@gmail.com
```

**Nota**: Para Gmail, necesitas una "Contraseña de aplicación" (no tu contraseña normal).

### 5. Ejecutar la Aplicación

```bash
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

---

## 🏗️ Arquitectura del Sistema

### Patrón MVC (Modelo-Vista-Controlador)

- **Modelo**: Funciones en `app.py` que interactúan con SQLite (`cargar_*`, `guardar_*`)
- **Vista**: Templates HTML en `templates/`
- **Controlador**: Rutas Flask (`@app.route`)

### Funciones Principales de Datos

Todas están en `app.py`:

```python
# Cargar datos
cargar_usuarios_db()          # Carga usuarios desde BD
cargar_pacientes()            # Carga pacientes
cargar_turnos()               # Carga turnos
cargar_agenda()               # Carga agenda médica
cargar_historias()            # Carga historias clínicas
cargar_pagos()                # Carga pagos

# Guardar datos
guardar_paciente()            # Guarda/actualiza paciente
guardar_turno()               # Guarda turno
guardar_historia_clinica()    # Guarda historia clínica
guardar_pago()                # Guarda pago
```

### Conexión a Base de Datos

```python
def get_db_connection():
    """Obtiene conexión con retry y configuración optimizada"""
    conn = sqlite3.connect("data/consultorio.db", timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")      # Modo WAL
    conn.execute("PRAGMA synchronous=NORMAL")    # Balance seguridad/velocidad
    conn.execute("PRAGMA busy_timeout=30000")     # 30 seg timeout
    return conn
```

**Características:**
- Retry automático con backoff exponencial
- Modo WAL para mejor concurrencia
- Timeout de 30 segundos para operaciones bloqueadas

---

## 🛣️ Rutas y Endpoints

### Rutas Públicas (Sin Autenticación)

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/` | GET | Página pública de inicio |
| `/reservar-turno` | GET | Formulario público de reserva |
| `/api/public/especialidades` | GET | Lista de especialidades disponibles |
| `/api/public/medicos` | GET | Médicos por especialidad |
| `/api/public/turnos-disponibles` | GET | Horarios disponibles |
| `/api/public/reservar-turno` | POST | Reservar turno (público) |

### Rutas de Autenticación

| Ruta | Método | Descripción |
|------|--------|-------------|
| `/login` | GET, POST | Login de usuarios |
| `/logout` | GET, POST | Cerrar sesión |

### Rutas Protegidas (Requieren Login)

#### Panel Principal
| Ruta | Método | Rol | Descripción |
|------|--------|-----|-------------|
| `/inicio` | GET | Todos | Panel principal según rol |

#### Gestión de Usuarios
| Ruta | Método | Rol | Descripción |
|------|--------|-----|-------------|
| `/api/usuarios` | GET | Todos | Listar usuarios |
| `/api/usuarios` | POST | Admin | Crear usuario |
| `/api/usuarios/<usuario>` | PUT | Admin | Actualizar usuario |
| `/api/usuarios/<usuario>` | DELETE | Admin | Eliminar usuario |

#### Gestión de Pacientes
| Ruta | Método | Rol | Descripción |
|------|--------|-----|-------------|
| `/pacientes` | GET | Secretaria | Vista de gestión de pacientes |
| `/api/pacientes` | GET | Secretaria | Listar pacientes |
| `/api/pacientes` | POST | Secretaria | Crear paciente |
| `/api/pacientes/<dni>` | GET | Secretaria | Obtener paciente |
| `/api/pacientes/<dni>` | PUT | Secretaria | Actualizar paciente |
| `/api/pacientes/<dni>` | DELETE | Secretaria | Eliminar paciente |

#### Gestión de Turnos
| Ruta | Método | Rol | Descripción |
|------|--------|-----|-------------|
| `/api/turnos` | GET | Todos | Listar turnos |
| `/api/turnos` | POST | Secretaria | Crear turno |
| `/api/turnos/<id>` | PUT | Secretaria | Actualizar turno |
| `/api/turnos/<id>/estado` | PUT | Secretaria | Cambiar estado |
| `/turnos-medico` | GET | Médico | Vista de turnos del médico |

#### Gestión de Agenda
| Ruta | Método | Rol | Descripción |
|------|--------|-----|-------------|
| `/agenda` | GET | Secretaria | Vista de gestión de agenda |
| `/api/agenda` | GET | Secretaria | Obtener agenda |
| `/api/agenda` | POST | Secretaria | Guardar horarios |

#### Historias Clínicas
| Ruta | Método | Rol | Descripción |
|------|--------|-----|-------------|
| `/historias/<dni>` | GET | Médico | Ver historia clínica |
| `/api/historias` | GET | Médico | Listar historias |
| `/api/historias` | POST | Médico | Crear historia |
| `/historias-gestion` | GET | Médico | Gestión de historias |

#### Pagos
| Ruta | Método | Rol | Descripción |
|------|--------|-----|-------------|
| `/api/pagos` | GET | Secretaria | Listar pagos |
| `/api/pagos` | POST | Secretaria | Registrar pago |

#### Reportes (Administrador)
| Ruta | Método | Rol | Descripción |
|------|--------|-----|-------------|
| `/administrador` | GET | Admin | Panel de administrador |
| `/api/reportes/ingresos` | GET | Admin | Reporte de ingresos |
| `/api/reportes/turnos` | GET | Admin | Reporte de turnos |

---

## 🎨 Templates y Frontend

### Estructura de Templates

Todos los templates usan **Jinja2** y están en `templates/`.

### Template Base

No hay un template base común, pero todos comparten:
- Bootstrap 5.3.3
- Bootstrap Icons
- Estilos personalizados inline o en `<style>`

### Templates Principales

#### 1. `inicio_publico.html`
- **Ruta**: `/`
- **Público**: Sí
- **Descripción**: Página de inicio pública con información del consultorio
- **Características**: Responsive, animaciones, diseño moderno

#### 2. `reserva_turno.html`
- **Ruta**: `/reservar-turno`
- **Público**: Sí
- **Descripción**: Formulario multi-paso para reservar turnos
- **Pasos**:
  1. Datos personales (DNI, email)
  2. Selección de especialidad
  3. Selección de médico
  4. Selección de fecha y hora
  5. Confirmación

#### 3. `login.html`
- **Ruta**: `/login`
- **Público**: Sí
- **Descripción**: Formulario de login
- **Características**: Validación, mensajes de error

#### 4. `index.html`
- **Ruta**: `/inicio` (médico/secretaria)
- **Protegido**: Sí
- **Descripción**: Panel principal según rol
- **Vista Médico**: Turnos del día, historias recientes
- **Vista Secretaria**: Turnos pendientes, estadísticas

#### 5. `secretaria.html`
- **Ruta**: `/secretaria`
- **Rol**: Secretaria
- **Descripción**: Panel completo de secretaria
- **Funcionalidades**:
  - Lista de turnos del día
  - Pacientes con registro rápido (datos incompletos)
  - Estadísticas
  - Accesos rápidos

#### 6. `pacientes.html`
- **Ruta**: `/pacientes`
- **Rol**: Secretaria
- **Descripción**: Gestión de pacientes
- **Funcionalidades**:
  - Crear/editar pacientes
  - Buscar pacientes
  - Completar datos de registro rápido (parámetro `?dni=XXXXX`)

#### 7. `agenda.html`
- **Ruta**: `/agenda`
- **Rol**: Secretaria
- **Descripción**: Gestión de agenda médica
- **Funcionalidades**:
  - Configurar horarios por médico y día
  - Asignar turnos
  - Ver disponibilidad

#### 8. `historia_clinica.html`
- **Ruta**: `/historias/<dni>`
- **Rol**: Médico
- **Descripción**: Vista de historia clínica de un paciente
- **Funcionalidades**:
  - Ver historias agrupadas por especialidad
  - Filtrar por especialidad
  - Agregar nueva consulta
  - Descargar PDF

#### 9. `administrador.html`
- **Ruta**: `/administrador`
- **Rol**: Administrador
- **Descripción**: Panel de administración
- **Funcionalidades**:
  - Reportes de ingresos
  - Estadísticas de turnos
  - Gestión de usuarios
  - Análisis de datos

### JavaScript en Templates

La mayoría de templates usan JavaScript vanilla (sin frameworks) para:
- Llamadas AJAX a APIs
- Validación de formularios
- Actualización dinámica de contenido
- Filtros y búsquedas

**Ejemplo de llamada API:**
```javascript
fetch('/api/pacientes')
    .then(response => response.json())
    .then(data => {
        // Procesar datos
    });
```

---

## 🔐 Sistema de Autenticación y Permisos

### Decoradores de Seguridad

```python
@login_requerido
def mi_ruta():
    # Requiere estar logueado
    pass

@rol_permitido(["administrador", "secretaria"])
def mi_ruta():
    # Requiere rol específico
    pass
```

### Sesiones

- **Duración**: 24 horas (configurable en `app.config['PERMANENT_SESSION_LIFETIME']`)
- **Almacenamiento**: Flask session (cookies firmadas)
- **Datos en sesión**:
  - `usuario`: Nombre de usuario
  - `rol`: Rol del usuario
  - `nombre_completo`: Nombre completo

### Hash de Contraseñas

```python
from werkzeug.security import generate_password_hash, check_password_hash

# Crear hash
hash = generate_password_hash("contraseña")

# Verificar
if check_password_hash(hash, "contraseña"):
    # Contraseña correcta
    pass
```

---

## 📧 Configuración de Email

### Variables de Entorno

Archivo `.env`:
```env
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=tu_email@gmail.com
MAIL_PASSWORD=contraseña_de_aplicacion
MAIL_FROM=tu_email@gmail.com
```

### Función de Envío

```python
enviar_email_confirmacion(destinatario, nombre_paciente, medico, fecha, hora, especialidad)
```

**Características:**
- Retry automático (2 intentos)
- Timeout extendido (30 segundos)
- Formato HTML y texto plano
- Incluye dirección del consultorio

### Probar Email

```bash
python probar_email.py
```

---

## 🔄 Flujos de Trabajo

### 1. Reserva Pública de Turno

```
1. Paciente accede a /reservar-turno
2. Completa DNI y email
3. Selecciona especialidad
4. Selecciona médico
5. Selecciona fecha y hora disponible
6. Confirma reserva
7. Sistema:
   - Crea/actualiza paciente (registro_rapido=1 si datos incompletos)
   - Crea turno (estado='sin atender')
   - Envía email de confirmación
8. Secretaria ve paciente en "Pacientes con Registro Rápido"
```

### 2. Recepción de Paciente

```
1. Secretaria ve turno en panel
2. Marca como "recepcionado"
3. Si paciente tiene registro_rapido=1:
   - Aparece destacado
   - Botón "Completar" pre-llena DNI
4. Secretaria completa datos del paciente
5. Turno queda listo para atención
```

### 3. Atención Médica

```
1. Médico ve turnos del día en /turnos-medico
2. Marca turno como "sala de espera"
3. Llama al paciente ("llamado")
4. Atiende al paciente
5. Accede a /historias/<dni>
6. Agrega nueva consulta
7. Marca turno como "atendido"
```

### 4. Gestión de Agenda

```
1. Secretaria accede a /agenda
2. Selecciona médico
3. Selecciona día de la semana
4. Agrega/elimina horarios
5. Sistema guarda en tabla `agenda`
6. Horarios disponibles se muestran en reserva pública
```

---

## 🛠️ Scripts Auxiliares

### `crear_todas_las_tablas.py`
Crea todas las tablas de la base de datos desde cero.

**Uso:**
```bash
python crear_todas_las_tablas.py
```

### `crear_usuario.py`
Crea usuarios desde la línea de comandos.

**Uso:**
```bash
python crear_usuario.py
```

**Campos solicitados:**
- Usuario
- Contraseña
- Rol (medico/secretaria/administrador)
- Especialidad (solo si es médico)

### `agregar_especialidad_medicos.py`
Migración: agrega columna `especialidad` a tabla `usuarios`.

**Uso:**
```bash
python agregar_especialidad_medicos.py
```

### `probar_email.py`
Prueba el envío de emails con la configuración actual.

**Uso:**
```bash
python probar_email.py
```

### `limpiar_turnos.py`
Limpia turnos antiguos (útil para mantenimiento).

**Uso:**
```bash
python limpiar_turnos.py
```

---

## 💻 Guía de Desarrollo

### Agregar una Nueva Ruta

```python
@app.route("/mi-ruta")
@login_requerido
@rol_permitido(["secretaria"])  # Opcional
def mi_ruta():
    # Lógica aquí
    return render_template("mi_template.html", datos=datos)
```

### Agregar un Nuevo Endpoint API

```python
@app.route("/api/mi-endpoint", methods=["GET", "POST"])
@login_requerido
def mi_endpoint():
    if request.method == "GET":
        # Obtener datos
        datos = obtener_datos()
        return jsonify(datos)
    elif request.method == "POST":
        # Guardar datos
        data = request.json
        guardar_datos(data)
        return jsonify({"success": True}), 201
```

### Agregar una Nueva Tabla

1. **Crear script de migración:**
```python
# migracion_nueva_tabla.py
import sqlite3

conn = sqlite3.connect('data/consultorio.db')
cursor = conn.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS nueva_tabla (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        campo1 TEXT NOT NULL,
        campo2 INTEGER,
        fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
    )
""")

conn.commit()
conn.close()
print("✅ Tabla creada")
```

2. **Agregar funciones de carga/guardado en `app.py`:**
```python
def cargar_nueva_tabla():
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM nueva_tabla")
    # Procesar resultados
    conn.close()
    return datos

def guardar_nueva_tabla(datos):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("INSERT INTO nueva_tabla ...", datos)
    conn.commit()
    conn.close()
```

### Modificar un Template Existente

1. Localizar template en `templates/`
2. Modificar HTML/CSS/JavaScript según necesidad
3. Si necesitas nuevos datos del backend, modificar la ruta correspondiente en `app.py`

**Ejemplo:**
```python
@app.route("/mi-vista")
def mi_vista():
    nuevos_datos = obtener_nuevos_datos()
    return render_template("mi_template.html", nuevos_datos=nuevos_datos)
```

### Agregar un Nuevo Campo a una Tabla

1. **Crear script de migración:**
```python
# agregar_campo_tabla.py
import sqlite3

conn = sqlite3.connect('data/consultorio.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE pacientes ADD COLUMN nuevo_campo TEXT")
    conn.commit()
    print("✅ Campo agregado")
except sqlite3.OperationalError as e:
    if "duplicate column" in str(e):
        print("⚠️ Campo ya existe")
    else:
        raise
finally:
    conn.close()
```

2. **Actualizar funciones de carga/guardado:**
```python
# En cargar_pacientes()
c.execute("SELECT dni, nombre, ..., nuevo_campo FROM pacientes")

# En guardar_paciente()
c.execute("INSERT INTO pacientes (..., nuevo_campo) VALUES (..., ?)", (valor,))
```

### Agregar un Nuevo Rol

1. **Actualizar validaciones en `app.py`:**
```python
@rol_permitido(["medico", "secretaria", "administrador", "nuevo_rol"])
```

2. **Actualizar lógica de redirección en `/inicio`:**
```python
if rol == "nuevo_rol":
    return render_template("nuevo_rol_panel.html")
```

3. **Crear template para el nuevo rol**

---

## 🐛 Solución de Problemas

### Error: "database is locked"

**Causa**: Múltiples conexiones simultáneas o conexión no cerrada.

**Solución**:
- Verificar que todas las conexiones se cierren con `conn.close()`
- El sistema tiene retry automático, pero si persiste:
  - Cerrar todas las instancias de la aplicación
  - Esperar unos segundos
  - Reiniciar

### Error: "No module named 'dotenv'"

**Solución**:
```bash
pip install python-dotenv
```

### Email no se envía

**Verificar**:
1. Archivo `.env` existe y tiene las variables correctas
2. Para Gmail: usar "Contraseña de aplicación" (no contraseña normal)
3. Probar con `python probar_email.py`

**Logs de debug**:
El sistema imprime logs detallados en consola sobre el envío de emails.

### Paciente con registro rápido no aparece

**Verificar**:
1. Campo `registro_rapido = 1` en tabla `pacientes`
2. Query en `secretaria.html` filtra correctamente
3. JavaScript carga la sección correctamente

### Horarios no aparecen en reserva pública

**Verificar**:
1. Agenda configurada en tabla `agenda`
2. Día de la semana en MAYÚSCULAS (LUNES, MARTES, etc.)
3. Médico tiene `activo = 1` en tabla `usuarios`
4. Endpoint `/api/public/turnos-disponibles` funciona correctamente

### Especialidad no se muestra en historias

**Verificar**:
1. Médico tiene `especialidad` asignada en tabla `usuarios`
2. Función `cargar_historias()` hace JOIN con `usuarios`
3. Template `historia_clinica.html` muestra el campo

---

## 📝 Notas Importantes

### Zona Horaria
- Sistema configurado para **Argentina (UTC-3)**
- Configuración en `app.py`: `timezone_ar = pytz.timezone('America/Argentina/Buenos_Aires')`

### Formato de Fechas
- **Base de datos**: `YYYY-MM-DD` (texto)
- **Display**: `DD/MM/YYYY` (formateado en frontend)
- **Horas**: `HH:MM` (24 horas)

### Backup de Base de Datos
- Backups automáticos en `data/consultorio_backup_*.db`
- Realizar backups manuales antes de cambios importantes:
```bash
cp data/consultorio.db data/consultorio_backup_manual_$(date +%Y%m%d_%H%M%S).db
```

### Seguridad
- **NO** commitear archivo `.env` (debe estar en `.gitignore`)
- Contraseñas siempre hasheadas (nunca en texto plano)
- Validar todos los inputs del usuario
- Usar parámetros preparados en queries SQL (prevenir SQL injection)

### Performance
- Base de datos usa modo WAL para mejor concurrencia
- Cache configurado en conexión SQLite
- Timeouts configurados para evitar bloqueos

---

## 📞 Contacto y Soporte

**Desarrollador**: Nicolas Fernandez

Para preguntas o modificaciones, consultar esta documentación primero. Si necesitas agregar funcionalidades complejas, seguir la guía de desarrollo en la sección correspondiente.

---

## 📚 Recursos Adicionales

- **Flask Documentation**: https://flask.palletsprojects.com/
- **SQLite Documentation**: https://www.sqlite.org/docs.html
- **Bootstrap 5**: https://getbootstrap.com/docs/5.3/
- **Jinja2 Templates**: https://jinja.palletsprojects.com/

---

**Última actualización**: 2025-01-XX
**Versión del sistema**: 1.0

