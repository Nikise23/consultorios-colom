# 🚀 Migración de JSON a Base de Datos SQLite

Este conjunto de scripts te permite migrar todos los datos de tu sistema de consultorio desde archivos JSON (como los que tienes en Render) a una base de datos SQLite local.

## 📋 Archivos incluidos

- `migracion_completa.py` - **Script principal** que coordina todo el proceso
- `migrar_json_a_db.py` - Script que realiza la migración de datos
- `verificar_migracion.py` - Script que verifica que la migración fue exitosa
- `preparar_migracion.py` - Script que ayuda a preparar los archivos JSON
- `exportar_desde_render.py` - Script con instrucciones para exportar desde Render

## 🛠️ Proceso de migración

### Paso 1: Preparar los archivos JSON

1. **Descarga los archivos JSON desde Render:**
   - Ve a tu dashboard de Render
   - Accede a la base de datos PostgreSQL
   - Ejecuta las consultas SQL para exportar los datos
   - Guarda los resultados como archivos JSON

2. **Archivos requeridos:**
   - `usuarios.json` - Datos de usuarios del sistema
   - `pacientes.json` - Datos de pacientes
   - `turnos.json` - Datos de turnos
   - `pagos.json` - Datos de pagos
   - `agenda.json` - Datos de agenda/horarios

3. **Formato de archivos JSON:**
   ```json
   [
     {
       "dni": "12345678",
       "nombre": "Juan",
       "apellido": "Pérez",
       "fecha_nacimiento": "1990-01-01",
       "celular": "1122334455",
       "email": "juan@email.com",
       "obra_social": "OSDE",
       "direccion": "Av. Principal 123",
       "activo": 1
     }
   ]
   ```

### Paso 2: Ejecutar la migración

1. **Coloca todos los archivos JSON** en la misma carpeta que los scripts
2. **Ejecuta el script principal:**
   ```bash
   python migracion_completa.py
   ```

3. **El script automáticamente:**
   - ✅ Verifica que todos los archivos estén presentes
   - ✅ Crea un backup de la base de datos actual
   - ✅ Vacía la base de datos SQLite
   - ✅ Migra todos los datos desde JSON
   - ✅ Verifica la integridad de los datos
   - ✅ Genera un reporte de migración

### Paso 3: Verificar la migración

El script genera automáticamente:
- `reporte_migracion.json` - Reporte detallado de la migración
- `consultorio_backup_YYYYMMDD_HHMMSS.db` - Backup de la base de datos anterior

## 🔍 Consultas SQL para exportar desde Render

### Exportar usuarios:
```sql
SELECT json_agg(
    json_build_object(
        'usuario', usuario,
        'contrasena', contrasena,
        'rol', rol,
        'nombre_completo', nombre_completo,
        'email', email,
        'telefono', telefono,
        'activo', activo
    )
) as usuarios
FROM usuarios;
```

### Exportar pacientes:
```sql
SELECT json_agg(
    json_build_object(
        'dni', dni,
        'nombre', nombre,
        'apellido', apellido,
        'fecha_nacimiento', fecha_nacimiento,
        'celular', celular,
        'email', email,
        'obra_social', obra_social,
        'direccion', direccion,
        'activo', activo
    )
) as pacientes
FROM pacientes;
```

### Exportar turnos:
```sql
SELECT json_agg(
    json_build_object(
        'dni_paciente', dni_paciente,
        'medico', medico,
        'fecha', fecha,
        'hora', hora,
        'estado', estado,
        'observaciones', observaciones,
        'fecha_creacion', fecha_creacion,
        'fecha_modificacion', fecha_modificacion
    )
) as turnos
FROM turnos;
```

### Exportar pagos:
```sql
SELECT json_agg(
    json_build_object(
        'dni_paciente', dni_paciente,
        'nombre_paciente', nombre_paciente,
        'fecha', fecha,
        'hora', hora,
        'monto', monto,
        'tipo_pago', tipo_pago,
        'obra_social', obra_social,
        'observaciones', observaciones,
        'fecha_creacion', fecha_creacion
    )
) as pagos
FROM pagos;
```

### Exportar agenda:
```sql
SELECT json_agg(
    json_build_object(
        'medico', medico,
        'dia_semana', dia_semana,
        'horario', horario
    )
) as agenda
FROM agenda;
```

## ⚠️ Consideraciones importantes

1. **Backup:** El script crea automáticamente un backup de tu base de datos actual
2. **Validación:** Todos los datos se validan antes de la migración
3. **Integridad:** Se verifican las relaciones entre tablas
4. **Rollback:** Si algo falla, puedes restaurar desde el backup

## 🚨 Solución de problemas

### Error: "Archivos JSON faltantes"
- Asegúrate de que todos los archivos JSON estén en la misma carpeta
- Verifica que los nombres de archivo sean exactos
- Usa `python preparar_migracion.py` para crear archivos de ejemplo

### Error: "Formato JSON inválido"
- Usa un validador JSON online para verificar el formato
- Asegúrate de que no haya comas finales
- Verifica que las fechas estén en formato ISO (YYYY-MM-DD)

### Error: "Base de datos bloqueada"
- Cierra todas las conexiones a la base de datos
- Reinicia el servidor Flask si está corriendo
- Ejecuta el script nuevamente

## 📞 Soporte

Si encuentras problemas durante la migración:

1. Revisa el archivo `reporte_migracion.json`
2. Verifica los logs de error en la consola
3. Asegúrate de que todos los archivos JSON tengan el formato correcto
4. Prueba con archivos de ejemplo primero

## 🎯 Próximos pasos después de la migración

1. **Probar el sistema localmente:**
   ```bash
   python app.py
   ```

2. **Verificar funcionalidades:**
   - Login con usuarios migrados
   - Visualización de pacientes
   - Gestión de turnos
   - Reportes de pagos

3. **Subir a Render:**
   - Subir todos los archivos modificados
   - Incluir la base de datos SQLite
   - Verificar que funcione en producción

¡La migración está lista para ejecutarse! 🚀






