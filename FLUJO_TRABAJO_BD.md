# 🔄 Flujo de Trabajo con Base de Datos

Esta guía explica el flujo correcto para trabajar con la base de datos en desarrollo y producción.

---

## 📊 Conceptos Importantes

### ¿Qué es la ESTRUCTURA de la BD?
- Tablas (ej: `bloqueos_agenda`, `usuarios`, `pacientes`)
- Columnas (ej: `activo`, `especialidad`, `email`)
- Índices, relaciones, etc.

### ¿Qué son los DATOS?
- Los registros dentro de las tablas
- Ej: usuarios, pacientes, turnos, historias clínicas

### ¿Qué se sube a Git?
- ✅ **CÓDIGO**: `app.py`, templates, scripts, etc.
- ✅ **ESTRUCTURA**: Scripts que crean/modifican tablas (`crear_todas_las_tablas.py`, `actualizar_base_datos.py`)
- ❌ **DATOS**: La base de datos NO se sube (está en `.gitignore`)

---

## 🔄 Flujo Completo

### Escenario 1: Trabajar con Datos de Producción Localmente

**Objetivo**: Trabajar localmente con los datos reales de producción.

1. **Descargar BD de producción**:
   - Ve a `https://tu-app.onrender.com/admin/backup-db` (como admin)
   - Descarga `consultorio_backup_YYYYMMDD_HHMMSS.db`

2. **Backup de BD local**:
   ```powershell
   Copy-Item data\consultorio.db data\consultorio_local_backup.db
   ```

3. **Reemplazar BD local**:
   ```powershell
   Move-Item consultorio_backup_*.db data\consultorio.db -Force
   ```

4. **Trabajar localmente** con los datos reales

5. **Al terminar** (opcional, restaurar BD local):
   ```powershell
   Move-Item data\consultorio_local_backup.db data\consultorio.db -Force
   ```

---

### Escenario 2: Agregar Nueva Funcionalidad (Nueva Tabla/Columna)

**Objetivo**: Agregar una nueva tabla o columna al sistema.

1. **Desarrollo local**:
   - Modificas el código (ej: agregas nueva tabla en `crear_todas_las_tablas.py`)
   - Ejecutas `python actualizar_base_datos.py` para actualizar la ESTRUCTURA localmente
   - Pruebas que funciona

2. **Commit y Push** (solo código):
   ```powershell
   git add app.py crear_todas_las_tablas.py actualizar_base_datos.py
   git commit -m "Agregar nueva funcionalidad X"
   git push
   ```

3. **En producción** (automático):
   - Render detecta el push
   - Ejecuta `build.sh` (que incluye `actualizar_base_datos.py`)
   - La ESTRUCTURA de la BD de producción se actualiza
   - Los DATOS de producción se mantienen intactos

---

### Escenario 3: Trabajar con Datos de Producción + Agregar Funcionalidad

**Objetivo**: Trabajar con datos reales Y agregar nueva funcionalidad.

1. **Descargar BD de producción** (ver Escenario 1)

2. **Agregar nueva funcionalidad**:
   - Modificas el código
   - Ejecutas `python actualizar_base_datos.py` para actualizar la ESTRUCTURA localmente
   - Pruebas con los datos reales

3. **Commit y Push** (solo código):
   ```powershell
   git add app.py crear_todas_las_tablas.py actualizar_base_datos.py
   git commit -m "Agregar nueva funcionalidad X"
   git push
   ```

4. **En producción** (automático):
   - La estructura se actualiza automáticamente
   - Los datos se mantienen

---

## ❓ Preguntas Frecuentes

### ¿Cuándo ejecuto `actualizar_base_datos.py`?

**Solo cuando agregas/modificas la ESTRUCTURA** (tablas, columnas):
- Agregaste una nueva tabla
- Agregaste una nueva columna
- Modificaste la estructura de una tabla

**NO lo ejecutes** si solo:
- Agregaste/modificaste datos
- Cambiaste código que no afecta la BD

### ¿Necesito ejecutar `actualizar_base_datos.py` antes de hacer commit?

**Sí, si agregaste nueva estructura**:
1. Ejecuta `python actualizar_base_datos.py` localmente
2. Prueba que funciona
3. Haz commit y push del código
4. En producción se ejecutará automáticamente

### ¿Los datos se actualizan cuando hago push?

**NO**. Los datos NO se suben a git. Solo se actualiza la ESTRUCTURA.

- **Local**: Tienes tus datos de prueba
- **Producción**: Tiene los datos reales
- Cada uno mantiene sus propios datos

### ¿Qué pasa si descargo la BD de producción?

- Obtienes una **copia** de los datos de producción
- Puedes trabajar localmente con datos reales
- Los cambios que hagas localmente **NO afectan** producción
- Es solo una copia para trabajar

### ¿Cómo actualizo los datos en producción?

Los datos en producción se actualizan:
- Cuando los usuarios usan la aplicación (reservan turnos, etc.)
- Cuando la secretaria registra pacientes
- Cuando los médicos crean historias clínicas
- **NO** se actualizan desde tu código local

---

## 📝 Resumen Visual

```
┌─────────────────────────────────────────────────────────┐
│                    DESARROLLO LOCAL                      │
├─────────────────────────────────────────────────────────┤
│ 1. Modificas código (app.py, templates, etc.)          │
│ 2. Si agregaste estructura → python actualizar_base_   │
│    datos.py                                             │
│ 3. Pruebas localmente                                   │
│ 4. git commit + git push (solo código)                 │
└─────────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────────┐
│                    PRODUCCIÓN (Render)                   │
├─────────────────────────────────────────────────────────┤
│ 1. git pull automático                                  │
│ 2. build.sh ejecuta actualizar_base_datos.py            │
│ 3. Estructura de BD se actualiza                        │
│ 4. Datos se mantienen intactos                          │
└─────────────────────────────────────────────────────────┘
```

---

## ✅ Checklist

Antes de hacer commit:

- [ ] ¿Agregué/modifiqué la estructura de la BD? → Ejecutar `actualizar_base_datos.py`
- [ ] ¿Probé que funciona localmente?
- [ ] ¿Hice commit solo del código (no la BD)?
- [ ] ¿La BD está en `.gitignore`? (verificar con `git status`)

---

## 🚨 Errores Comunes

### Error: "no such table: bloqueos_agenda"
**Solución**: Ejecuta `python actualizar_base_datos.py`

### Error: "no such column: activo"
**Solución**: Ejecuta `python actualizar_base_datos.py`

### Subí la BD a git por error
**Solución**: 
```powershell
git rm --cached data/consultorio.db
git commit -m "Remover BD del repositorio"
```
Verifica que esté en `.gitignore`

