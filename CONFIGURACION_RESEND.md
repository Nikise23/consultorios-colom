# 📧 Configuración de Resend para Envío de Emails

## ¿Por qué Resend?

Render (plan gratuito) **bloquea conexiones SMTP salientes** para prevenir spam. El error `[Errno 101] Network is unreachable` indica que no se puede conectar a Gmail SMTP.

**Solución**: Usar Resend, un servicio de email con API REST que funciona perfectamente en Render.

---

## 🚀 Pasos para Configurar Resend

### 1. Crear cuenta en Resend

1. Ve a: https://resend.com
2. Crea una cuenta gratuita (100 emails/día gratis)
3. Verifica tu email

### 2. Obtener API Key

1. En el dashboard de Resend → **"API Keys"**
2. Click en **"Create API Key"**
3. Dale un nombre (ej: "Consultorios Colom")
4. Copia el API Key (solo se muestra una vez)

### 3. Configurar dominio (opcional pero recomendado)

**Opción A: Usar dominio propio (recomendado para producción)**
- En Resend → **"Domains"** → **"Add Domain"**
- Sigue las instrucciones para verificar tu dominio
- Usa ese dominio como `RESEND_FROM_EMAIL`

**Opción B: Usar dominio de prueba (solo para testing)**
- Resend te da un dominio de prueba: `onboarding@resend.dev`
- Funciona solo para testing, no para producción

### 4. Configurar en Render

En Render Dashboard → tu servicio → **"Environment"** → Agrega:

| Variable | Valor | Descripción |
|----------|-------|-------------|
| `RESEND_API_KEY` | `re_xxxxxxxxxxxxx` | Tu API Key de Resend |
| `RESEND_FROM_EMAIL` | `Consultorios Colom <noreply@tudominio.com>` | Email remitente (formato: `Nombre <email@dominio.com>`) |

**Ejemplo:**
```
RESEND_API_KEY=re_abc123xyz789
RESEND_FROM_EMAIL=Consultorios Colom <noreply@consultorioscolom.com>
```

### 5. Reiniciar el servicio

Después de agregar las variables, Render se reiniciará automáticamente.

---

## ✅ Verificación

1. Intenta reservar un turno desde la página pública
2. Revisa los logs de Render - deberías ver:
   ```
   📧 [EMAIL] Usando Resend (API REST) para envío
   📧 [RESEND] Enviando email a...
   ✅ [RESEND] Email enviado exitosamente
   ```
3. Revisa la bandeja de entrada del paciente

---

## 🔄 Fallback a SMTP

Si `RESEND_API_KEY` no está configurado, el sistema intentará usar SMTP (solo funciona en desarrollo local, no en Render).

---

## 💰 Planes de Resend

- **Free**: 100 emails/día, 3,000 emails/mes
- **Pro**: $20/mes - 50,000 emails/mes
- **Business**: $80/mes - 200,000 emails/mes

Para un consultorio pequeño, el plan gratuito es suficiente.

---

## 📝 Notas

- Los emails se envían de forma asíncrona (no bloquean la respuesta)
- El sistema automáticamente usa Resend si está configurado
- No necesitas cambiar código, solo configurar las variables de entorno

