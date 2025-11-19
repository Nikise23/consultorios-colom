# Prompt Completo: Sistema de Consultorio Médico con Especialidades

## Contexto General

Necesito desarrollar un sistema de gestión de consultorio médico completo que permita:

1. **Gestión de usuarios** con diferentes roles (médico, secretaria, administrador)
2. **Gestión de pacientes** con información completa
3. **Gestión de turnos** con estados (sin atender, recepcionado, sala de espera, llamado, atendido, ausente)
4. **Sistema de pagos** con diferentes métodos (efectivo, transferencia, obra social)
5. **Agenda médica** configurable por médico y día de la semana
6. **Historias clínicas** con agrupación por especialidad médica
7. **Reportes y estadísticas** para administradores

## Requisitos Funcionales Específicos

### 1. Sistema de Especialidades Médicas

**Requisito principal:** Cada médico debe tener una especialidad asignada (Oftalmología, Traumatología, Pediatría, Clínica Médica, Cardiología, Dermatología, etc.)

**Funcionalidades requeridas:**
- Al crear un médico, debe poder asignarse una especialidad
- Las historias clínicas deben agruparse automáticamente por especialidad del médico que las realizó
- En la vista de historia clínica del paciente, debe haber botones/filtros para ver historias por especialidad
- Al hacer clic en una especialidad, mostrar solo las historias de esa especialidad
- Mostrar contador de consultas por especialidad
- Permitir ver "Todas las consultas" agrupadas por especialidad

### 2. Estructura de Base de Datos

**Tabla: usuarios**
```sql
CREATE TABLE usuarios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario TEXT UNIQUE NOT NULL,
    contrasena TEXT NOT NULL,
    rol TEXT NOT NULL,  -- 'medico', 'secretaria', 'administrador'
    nombre_completo TEXT,
    email TEXT,
    telefono TEXT,
    especialidad TEXT,  -- IMPORTANTE: Solo para médicos
    activo INTEGER DEFAULT 1,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP
)
```

**Tabla: pacientes**
```sql
CREATE TABLE pacientes (
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
```

**Tabla: turnos**
```sql
CREATE TABLE turnos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dni_paciente TEXT NOT NULL,
    medico TEXT NOT NULL,  -- Referencia al usuario médico
    fecha_turno TEXT NOT NULL,
    hora_turno TEXT NOT NULL,
    estado TEXT DEFAULT 'sin atender',  -- sin atender, recepcionado, sala de espera, llamado, atendido, ausente
    tipo_consulta TEXT,
    costo REAL DEFAULT 0,
    pagado INTEGER DEFAULT 0,
    observaciones TEXT,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dni_paciente) REFERENCES pacientes (dni)
)
```

**Tabla: historias_clinicas**
```sql
CREATE TABLE historias_clinicas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dni TEXT NOT NULL,
    consulta_medica TEXT NOT NULL,
    medico TEXT NOT NULL,  -- Referencia al usuario médico
    fecha_consulta TEXT NOT NULL,
    fecha_creacion TEXT NOT NULL,
    FOREIGN KEY (dni) REFERENCES pacientes (dni)
)
```

**Tabla: pagos**
```sql
CREATE TABLE pagos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dni_paciente TEXT NOT NULL,
    fecha_pago TEXT NOT NULL,
    monto REAL NOT NULL,
    metodo_pago TEXT DEFAULT 'efectivo',  -- efectivo, transferencia, obra_social
    obra_social TEXT,
    observaciones TEXT,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (dni_paciente) REFERENCES pacientes (dni)
)
```

**Tabla: agenda**
```sql
CREATE TABLE agenda (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    medico TEXT NOT NULL,
    dia_semana TEXT NOT NULL,  -- LUNES, MARTES, MIERCOLES, JUEVES, VIERNES, SABADO, DOMINGO
    horario TEXT NOT NULL,
    activo INTEGER DEFAULT 1,
    fecha_creacion TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(medico, dia_semana, horario)
)
```

### 3. Funcionalidades Backend (Flask/Python)

#### 3.1 Gestión de Usuarios

**Endpoint: GET /api/usuarios**
- Debe retornar todos los usuarios con sus especialidades
- Incluir campo `especialidad` en la respuesta (null para no médicos)

**Endpoint: POST /api/usuarios**
- Crear nuevo usuario
- Si el rol es "medico", permitir asignar especialidad
- Validar que especialidad solo se asigne a médicos
- Campos requeridos: usuario, contrasena, rol
- Campo opcional: especialidad (solo si rol = "medico")

**Endpoint: PUT /api/usuarios/<usuario>**
- Actualizar usuario existente
- Permitir actualizar especialidad de médicos
- Si se cambia rol de médico a otro, eliminar especialidad

**Función: cargar_usuarios_db()**
- Debe incluir el campo `especialidad` en la consulta SQL
- Retornar especialidad en el diccionario de respuesta

#### 3.2 Gestión de Historias Clínicas

**Función: cargar_historias()**
- Cargar todas las historias clínicas
- Hacer JOIN o consulta separada para obtener especialidad de cada médico
- Incluir campo `especialidad` en cada historia retornada
- La especialidad debe obtenerse de la tabla usuarios donde rol = 'medico'

**Endpoint: GET /api/historias**
- Retornar todas las historias con especialidad incluida
- Usar función cargar_historias() actualizada

**Endpoint: GET /historias/<dni>**
- Obtener historias de un paciente específico
- Incluir especialidad en cada historia
- Ordenar por fecha_consulta DESC

**Endpoint: POST /historias**
- Guardar nueva historia clínica
- El médico se obtiene de la sesión actual
- Validar que el médico existe y tiene especialidad asignada

**Endpoint: GET /api/historias/buscar**
- Buscar historias con filtros (búsqueda, paginación, ordenamiento)
- Agrupar historias por especialidad en la respuesta
- Retornar estructura:
  ```json
  {
    "pacientes": [...],
    "especialidades": [
      {
        "especialidad": "Oftalmología",
        "historias": [...],
        "medicos": ["Dr. Juan", "Dr. María"],
        "total_consultas": 15
      }
    ],
    "total": 50,
    "pagina": 1,
    "por_pagina": 10,
    "total_paginas": 5
  }
  ```

### 4. Funcionalidades Frontend (HTML/JavaScript)

#### 4.1 Vista de Historia Clínica del Paciente

**Ubicación:** `/historia/<dni>`

**Componentes requeridos:**

1. **Filtros por Especialidad**
   - Botón "Todas las consultas" (activo por defecto)
   - Botón por cada especialidad encontrada en el historial
   - Cada botón debe mostrar:
     - Icono según especialidad (oftalmología: ojo, traumatología: hueso, etc.)
     - Nombre de la especialidad
     - Badge con contador de consultas

2. **Agrupación de Historias**
   - Al seleccionar "Todas": mostrar todas agrupadas por especialidad con encabezados
   - Al seleccionar una especialidad: mostrar solo esas historias
   - Ordenar por fecha (más reciente primero) dentro de cada grupo

3. **Estilos CSS**
   - Botones de especialidad con hover effects
   - Estado activo visualmente destacado
   - Transiciones suaves
   - Diseño responsive

**Código JavaScript requerido:**

```javascript
// Variables globales
let historiasPorEspecialidad = {};
let especialidadActual = 'todas';

// Función: cargarHistorial()
// - Cargar historias desde /api/historias
// - Filtrar por DNI del paciente
// - Agrupar por especialidad
// - Llamar a crearFiltrosEspecialidad()
// - Llamar a mostrarHistoriasAgrupadas()

// Función: crearFiltrosEspecialidad()
// - Crear botón "Todas las consultas" con contador total
// - Para cada especialidad única:
//   - Crear botón con icono apropiado
//   - Mostrar contador de consultas
//   - Asignar onclick para filtrar

// Función: filtrarPorEspecialidad(especialidad)
// - Actualizar especialidadActual
// - Marcar botón activo
// - Llamar a mostrarHistoriasAgrupadas()

// Función: mostrarHistoriasAgrupadas()
// - Si especialidadActual === 'todas':
//   - Mostrar todas agrupadas por especialidad con encabezados
// - Si no:
//   - Mostrar solo historias de esa especialidad
// - Ordenar por fecha dentro de cada grupo
```

**Iconos sugeridos por especialidad:**
- Oftalmología: `bi-eye`
- Traumatología: `bi-bone`
- Pediatría: `bi-heart`
- Clínica Médica: `bi-heart-pulse`
- Cardiología: `bi-heart-pulse-fill`
- Dermatología: `bi-droplet`
- General: `bi-file-medical`

### 5. Scripts de Migración y Utilidades

#### 5.1 Script de Migración de Base de Datos

**Archivo: agregar_especialidad_medicos.py**

```python
#!/usr/bin/env python3
"""
Script para agregar columna 'especialidad' a tabla 'usuarios'
"""
import sqlite3
import os

DB_PATH = "data/consultorio.db"

def agregar_columna_especialidad():
    if not os.path.exists(DB_PATH):
        print(f"❌ Error: No se encuentra la base de datos en {DB_PATH}")
        return False
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Verificar si la columna ya existe
        cursor.execute("PRAGMA table_info(usuarios)")
        columnas = [col[1] for col in cursor.fetchall()]
        
        if 'especialidad' in columnas:
            print("✅ La columna 'especialidad' ya existe")
            return True
        
        # Agregar la columna
        cursor.execute("ALTER TABLE usuarios ADD COLUMN especialidad TEXT")
        conn.commit()
        print("✅ Columna 'especialidad' agregada exitosamente")
        return True
    except sqlite3.Error as e:
        print(f"❌ Error: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()
```

#### 5.2 Script de Creación de Usuarios

**Funcionalidad:**
- Al crear usuario con rol "medico", preguntar por especialidad
- Mostrar lista de especialidades comunes
- Permitir ingresar especialidad personalizada
- Validar que especialidad solo se asigne a médicos

### 6. Autenticación y Autorización

**Roles:**
- **medico**: Puede ver y crear historias clínicas, ver sus turnos
- **secretaria**: Puede gestionar pacientes, turnos, pagos, agenda
- **administrador**: Acceso completo, incluyendo gestión de usuarios y reportes

**Decoradores requeridos:**
- `@login_requerido`: Verificar sesión activa
- `@rol_requerido(rol)`: Verificar rol específico
- `@rol_permitido([roles])`: Verificar que el rol esté en la lista

### 7. Consideraciones Técnicas

#### 7.1 Base de Datos
- Usar SQLite con modo WAL para mejor concurrencia
- Implementar timeouts y reintentos para evitar bloqueos
- Usar transacciones para operaciones críticas

#### 7.2 APIs
- Todas las respuestas en JSON
- Manejo de errores consistente con códigos HTTP apropiados
- Validación de datos en backend
- Sanitización de inputs

#### 7.3 Frontend
- Usar Bootstrap 5 para estilos
- Bootstrap Icons para iconos
- JavaScript vanilla (sin frameworks adicionales)
- Responsive design
- Manejo de errores con mensajes claros

### 8. Flujos de Trabajo Principales

#### 8.1 Flujo de Atención Médica
1. Secretaria asigna turno
2. Paciente llega → Secretaria marca como "recepcionado"
3. Secretaria registra pago → Estado cambia a "sala de espera"
4. Médico llama paciente → Estado cambia a "llamado"
5. Médico atiende → Estado cambia a "atendido"
6. Médico guarda historia clínica (se asocia automáticamente con su especialidad)

#### 8.2 Flujo de Consulta de Historia Clínica
1. Médico accede a historia clínica del paciente
2. Sistema carga todas las historias del paciente
3. Sistema agrupa por especialidad del médico que las realizó
4. Sistema muestra botones de filtro por especialidad
5. Médico puede:
   - Ver todas las consultas agrupadas
   - Filtrar por especialidad específica
   - Ver contadores por especialidad

### 9. Ejemplos de Datos

**Especialidades comunes:**
- Oftalmología
- Traumatología
- Pediatría
- Clínica Médica
- Cardiología
- Dermatología
- Ginecología
- Neurología
- Psiquiatría
- Otorrinolaringología

**Estados de turno:**
- sin atender
- recepcionado
- sala de espera
- llamado
- atendido
- ausente

**Métodos de pago:**
- efectivo
- transferencia
- obra_social

### 10. Mejoras Futuras Sugeridas

1. **Búsqueda avanzada** en historias clínicas por texto, fecha, especialidad
2. **Exportación** de historias por especialidad a PDF
3. **Gráficos** de consultas por especialidad
4. **Notificaciones** cuando hay nuevas historias de una especialidad
5. **Filtros combinados** (especialidad + fecha + médico)
6. **Historial de cambios** en historias clínicas
7. **Plantillas** de consulta por especialidad
8. **Integración** con sistemas externos (laboratorios, imágenes)

### 11. Estructura de Archivos Sugerida

```
consultorio/
├── app.py                          # Aplicación principal Flask
├── data/
│   └── consultorio.db              # Base de datos SQLite
├── templates/
│   ├── historia_clinica.html       # Vista de historia clínica con filtros
│   ├── turnos_medico.html          # Vista de turnos para médico
│   ├── secretaria.html              # Vista de secretaria
│   ├── administrador.html           # Vista de administrador
│   └── ...
├── static/
│   ├── css/
│   └── js/
├── crear_usuario.py                 # Script para crear usuarios
├── agregar_especialidad_medicos.py  # Script de migración
└── crear_todas_las_tablas.py        # Script de creación de tablas
```

### 12. Puntos Críticos a Considerar

1. **Especialidad es opcional**: Los médicos pueden no tener especialidad asignada inicialmente
2. **Histórico**: Las historias antiguas pueden no tener especialidad si el médico no la tenía asignada
3. **Cambios de especialidad**: Si un médico cambia de especialidad, las historias antiguas mantienen la especialidad original
4. **Múltiples especialidades**: Un médico puede tener solo una especialidad (si se necesita múltiples, considerar tabla de relación)
5. **Sin especialidad**: Agrupar historias de médicos sin especialidad en "Sin especialidad"

### 13. Testing y Validación

**Casos de prueba importantes:**
1. Crear médico con especialidad
2. Crear médico sin especialidad
3. Actualizar especialidad de médico existente
4. Ver historias agrupadas por especialidad
5. Filtrar historias por especialidad
6. Ver historias de médico sin especialidad
7. Cambiar rol de médico a secretaria (debe eliminar especialidad)
8. Crear historia clínica y verificar que se asocia correctamente

---

## Resumen Ejecutivo

Este sistema permite gestionar un consultorio médico completo con la funcionalidad clave de **agrupar historias clínicas por especialidad médica**. Los médicos pueden ver fácilmente el historial de consultas de un paciente filtrado por especialidad, lo que facilita el seguimiento de tratamientos específicos y la continuidad de la atención médica.

**Características distintivas:**
- ✅ Especialidades médicas asignadas a cada médico
- ✅ Agrupación automática de historias por especialidad
- ✅ Filtrado interactivo en la interfaz
- ✅ Contadores y estadísticas por especialidad
- ✅ Diseño intuitivo y responsive

**Tecnologías principales:**
- Backend: Python + Flask
- Base de datos: SQLite
- Frontend: HTML + JavaScript + Bootstrap 5
- Autenticación: Sesiones Flask con roles

---

*Este prompt puede ser usado como base para desarrollar sistemas similares de gestión médica o de consultorios con requerimientos de agrupación y filtrado por categorías especializadas.*

