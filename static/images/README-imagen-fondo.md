# Instrucciones para agregar la imagen de fondo del consultorio

## Pasos para implementar tu imagen:

1. **Guarda tu imagen** en la carpeta `static/images/` con el nombre `consultorio-background.jpg`

2. **Formatos soportados:**
   - JPG/JPEG (recomendado)
   - PNG
   - WebP

3. **Tamaño recomendado:**
   - Resolución: 1920x1080 o superior
   - Peso: máximo 2MB para mejor rendimiento

## Si prefieres usar un nombre diferente:

Si quieres usar un nombre diferente para tu imagen, simplemente cambia esta línea en `templates/login.html`:

```css
background-image: url('static/images/consultorio-background.jpg');
```

Por ejemplo, si tu imagen se llama `mi-imagen.jpg`:

```css
background-image: url('static/images/mi-imagen.jpg');
```

## Características del diseño implementado:

✅ **Imagen de fondo** con la foto del consultorio
✅ **Overlay semi-transparente** para mejorar la legibilidad
✅ **Efecto blur** sutil en el fondo
✅ **Diseño responsive** que se adapta a móviles
✅ **Animaciones suaves** para una mejor experiencia
✅ **Colores del consultorio** (rojo) integrados en el diseño
✅ **Logo del hospital** con efectos visuales
✅ **Footer con tu nombre** como desarrollador

## Personalización adicional:

Si quieres ajustar la transparencia del overlay, modifica esta línea:

```css
background: rgba(255, 255, 255, 0.75);
```

- `0.75` = 75% de opacidad (más transparente = más visible la imagen)
- `0.85` = 85% de opacidad (menos transparente = menos visible la imagen)

¡Una vez que agregues tu imagen, el login tendrá un aspecto profesional y personalizado con la identidad visual del consultorio!



