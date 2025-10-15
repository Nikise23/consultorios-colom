import json
import shutil
from datetime import datetime, timedelta

ARCHIVO_TURNOS = "data/turnos.json"
BACKUP = "turnos_backup.json"

# Hacer backup
shutil.copy2(ARCHIVO_TURNOS, BACKUP)
print(f"Backup creado: {BACKUP}")

with open(ARCHIVO_TURNOS, "r", encoding="utf-8") as f:
    turnos = json.load(f)

ahora = datetime.now()
turnos_filtrados = []
eliminados = []

for t in turnos:
    fecha_hora_str = f"{t.get('fecha', '')} {t.get('hora', '00:00')}"
    try:
        fecha_hora = datetime.strptime(fecha_hora_str, "%Y-%m-%d %H:%M")
    except Exception:
        turnos_filtrados.append(t)
        continue
    # Si está vencido hace más de 24hs y es 'sin atender', eliminar
    if t.get('estado', '').lower() == 'sin atender' and fecha_hora < ahora - timedelta(hours=24):
        eliminados.append(t)
    else:
        turnos_filtrados.append(t)

with open(ARCHIVO_TURNOS, "w", encoding="utf-8") as f:
    json.dump(turnos_filtrados, f, indent=2, ensure_ascii=False)

print(f"Turnos eliminados: {len(eliminados)}")
if eliminados:
    for t in eliminados:
        print(f"- {t.get('fecha')} {t.get('hora')} | {t.get('medico')} | {t.get('dni_paciente')} | {t.get('estado')}")
else:
    print("No se eliminaron turnos.")

