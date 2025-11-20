# 💾 Guía: Configurar Disco Persistente en Render

Esta guía te explica cómo configurar un disco persistente en Render para que tu base de datos SQLite se mantenga entre reinicios.

---

## 📋 Paso 1: Comprar Disco Persistente en Render

1. Ve a tu servicio en Render Dashboard
2. Ve a la pestaña **"Settings"** (Configuración)
3. Busca la sección **"Persistent Disk"** o **"Disk"**
4. Click en **"Add Disk"** o **"Attach Disk"**
5. Selecciona el tamaño (mínimo recomendado: 1 GB)
6. Configura el **Mount Path**: `/data` (o el que prefieras)
7. Guarda los cambios

**Costo aproximado**: $0.25/GB por mes (1 GB = $0.25/mes)

---

## ⚙️ Paso 2: Configurar Variable de Entorno

1. En Render Dashboard → tu servicio → **"Environment"**
2. Agrega una nueva variable de entorno:

   | Variable | Valor | Descripción |
   |----------|-------|-------------|
   | `RENDER_DISK_PATH` | `/data` | Ruta donde se monta el disco persistente |

3. Guarda los cambios

**Nota**: El valor debe coincidir con el **Mount Path** que configuraste en el Paso 1.

---

## 🔄 Paso 3: Reiniciar el Servicio

Después de agregar el disco y la variable de entorno:

1. Render reiniciará automáticamente el servicio
2. O puedes hacerlo manualmente: **"Manual Deploy"** → **"Clear build cache & deploy"**

---

## ✅ Paso 4: Verificar que Funciona

1. Después del reinicio, la aplicación debería:
   - Crear la base de datos en `/data/consultorio.db` (si no existe)
   - Usar el disco persistente para guardar datos

2. Para verificar:
   - Crea un usuario o reserva un turno
   - Reinicia el servicio manualmente
   - Verifica que los datos se mantienen

---

## 📁 Estructura de Archivos

Con disco persistente configurado:

```
/opt/render/project/src/          # Código de la aplicación (se reinicia)
├── app.py
├── templates/
└── ...

/data/                            # Disco persistente (NO se reinicia)
└── consultorio.db                # Base de datos SQLite
```

---

## 🔧 Configuración Alternativa (Sin Variable de Entorno)

Si prefieres no usar la variable de entorno, puedes modificar `app.py` directamente:

```python
# En get_db_path(), cambiar:
def get_db_path():
    # Usar disco persistente directamente
    os.makedirs('/data', exist_ok=True)
    return '/data/consultorio.db'
```

**Nota**: Esto solo funcionará en Render. Para desarrollo local, necesitarías mantener la lógica de fallback.

---

## ⚠️ Importante

### Antes de Configurar el Disco

Si ya tienes datos en producción:

1. **Hacer backup de la BD actual**:
   - Ve a `/admin/backup-db` (como admin)
   - Descarga la base de datos

2. **Después de configurar el disco**:
   - La aplicación creará una BD nueva en `/data/`
   - Puedes subir tu BD local usando `/setup-upload-db`
   - O esperar a que se cree automáticamente

### Migración de Datos

Si ya tienes datos en `data/consultorio.db` (sin disco persistente):

1. Los datos están en el sistema de archivos efímero
2. Al configurar el disco, se creará una BD nueva en `/data/`
3. Necesitarás subir tus datos usando `/setup-upload-db`

---

## 💰 Costos

- **Disco Persistente**: $0.25/GB por mes
- **Ejemplo**: 1 GB = $0.25/mes, 5 GB = $1.25/mes
- **Recomendación**: Empieza con 1 GB, puedes aumentar después

---

## ❓ Preguntas Frecuentes

**P: ¿Necesito cambiar el código?**
R: No, el código ya está preparado. Solo necesitas configurar el disco y la variable de entorno.

**P: ¿Qué pasa si no configuro el disco?**
R: La aplicación seguirá funcionando, pero los datos pueden perderse en reinicios (sistema de archivos efímero).

**P: ¿Puedo cambiar el tamaño del disco después?**
R: Sí, puedes aumentar el tamaño en cualquier momento desde Render Dashboard.

**P: ¿Los datos se sincronizan automáticamente?**
R: No, SQLite no se sincroniza. El disco persistente solo asegura que los datos no se pierdan en reinicios.

---

## 🎯 Resumen

1. ✅ Comprar disco persistente en Render (mínimo 1 GB)
2. ✅ Configurar Mount Path: `/data`
3. ✅ Agregar variable de entorno: `RENDER_DISK_PATH=/data`
4. ✅ Reiniciar servicio
5. ✅ Verificar que funciona

¡Listo! Tu base de datos ahora se guardará en el disco persistente y no se perderá en reinicios.

