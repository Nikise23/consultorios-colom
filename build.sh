#!/bin/bash
# Script de build para Render.com
# Este script se ejecuta automáticamente en cada despliegue

echo "🔧 Instalando dependencias..."
pip install -r requirements.txt

echo "📋 Creando/actualizando tablas de la base de datos..."
python crear_todas_las_tablas.py

echo "🔄 Actualizando base de datos con nuevas migraciones..."
python actualizar_base_datos.py

echo "✅ Build completado"

