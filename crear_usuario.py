import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "data/consultorio.db"


#----------- Validaciones -----------
def input_no_vacio(mensaje):
    """
    Pide input hasta que el usuario escriba algo no vacío.
    Evita que con solo ENTER se continúe.
    """
    while True:
        dato = input(mensaje).strip()
        if dato:
            return dato
        print("❌ El campo no puede quedar vacío.")

# ---------- utilidades de archivo ----------
def cargar_usuarios():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, usuario, contrasena, rol FROM usuarios")
    usuarios = [dict(zip([desc[0] for desc in c.description], row)) for row in c.fetchall()]
    conn.close()
    return usuarios

def agregar_usuario(usuario, contrasena, rol, especialidad=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if especialidad and rol == "medico":
        c.execute("INSERT INTO usuarios (usuario, contrasena, rol, especialidad) VALUES (?, ?, ?, ?)", 
                  (usuario, generate_password_hash(contrasena), rol, especialidad))
    else:
        c.execute("INSERT INTO usuarios (usuario, contrasena, rol) VALUES (?, ?, ?)", 
                  (usuario, generate_password_hash(contrasena), rol))
    conn.commit()
    conn.close()

def eliminar_usuarios_repetidos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Elimina usuarios con el mismo nombre, dejando solo el de menor id
    c.execute('''DELETE FROM usuarios WHERE id NOT IN (
        SELECT MIN(id) FROM usuarios GROUP BY usuario
    )''')
    conn.commit()
    conn.close()

def eliminar_usuario_db_por_id(user_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM usuarios WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

def eliminar_usuario_db(usuario):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM usuarios WHERE usuario = ?", (usuario,))
    conn.commit()
    conn.close()

def reiniciar_usuarios():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM usuarios")
    conn.commit()
    conn.close()

def crear_usuario():
    print("\n--- Crear nuevo usuario ---")
    usuario = input_no_vacio("Nombre de usuario: ")

    # contraseña y confirmación
    while True:
        contrasena = input_no_vacio("Contraseña: ")
        confirmar = input_no_vacio("Confirmar contraseña: ")
        if contrasena == confirmar:
            break
        print("❌ Las contraseñas no coinciden. Intentá de nuevo.")

    # rol
    while True:
        rol = input_no_vacio("Rol (medico / secretaria / administrador): ").lower()
        if rol in ("medico", "secretaria", "administrador"):
            break
        print("❌ Rol inválido. Debe ser 'medico', 'secretaria' o 'administrador'.")

    # especialidad (solo para médicos)
    especialidad = None
    if rol == "medico":
        print("\nEspecialidades comunes:")
        print("  - Oftalmología")
        print("  - Traumatología")
        print("  - Pediatría")
        print("  - Clínica Médica")
        print("  - Cardiología")
        print("  - Dermatología")
        print("  - Otras...")
        especialidad = input("Especialidad (opcional, presione Enter para omitir): ").strip()
        if not especialidad:
            especialidad = None

    usuarios = cargar_usuarios()
    if any(u["usuario"] == usuario for u in usuarios):
        print("❌ Ese usuario ya existe.")
        return
    agregar_usuario(usuario, contrasena, rol, especialidad)
    mensaje = f"✅ Usuario '{usuario}' creado con rol '{rol}'"
    if especialidad:
        mensaje += f" y especialidad '{especialidad}'"
    mensaje += "."
    print(mensaje)

def eliminar_usuario():
    print("\n--- Eliminar usuario ---")
    usuarios = cargar_usuarios()
    if not usuarios:
        print("No hay usuarios registrados.")
        return

    print("Usuarios:")
    for u in usuarios:
        print(f"ID: {u['id']} • {u['usuario']} ({u['rol']})")
    try:
        id_eliminar = int(input_no_vacio("ID de usuario a eliminar: "))
    except ValueError:
        print("❌ ID inválido.")
        return
    if not any(u["id"] == id_eliminar for u in usuarios):
        print("❌ Usuario no encontrado.")
    else:
        eliminar_usuario_db_por_id(id_eliminar)
        print(f"✅ Usuario con ID {id_eliminar} eliminado.")

def reiniciar_archivo():
    print("\n--- Reiniciar archivo de usuarios ---")
    confirmar = input(
        "Escribí 'SI' para confirmar que querés borrar TODOS los usuarios: "
    )
    if confirmar.upper() == "SI":
        reiniciar_usuarios()
        print("✅ Todos los usuarios eliminados de la base de datos.")
    else:
        print("Operación cancelada.")

def borrar_repetidos():
    eliminar_usuarios_repetidos()
    print("✅ Usuarios repetidos eliminados (por nombre de usuario, se conserva el de menor ID).")


# ---------- menú principal ----------
def menu():
    while True:
        print("\n=== Gestión de Usuarios ===")
        print("1. Crear nuevo usuario")
        print("2. Eliminar usuario por ID")
        print("3. Reiniciar usuarios")
        print("4. Borrar usuarios repetidos")
        print("5. Salir")

        opcion = input("Elegí una opción: ").strip()
        if opcion == "1":
            crear_usuario()
        elif opcion == "2":
            eliminar_usuario()
        elif opcion == "3":
            reiniciar_archivo()
        elif opcion == "4":
            borrar_repetidos()
        elif opcion == "5":
            print("¡Hasta luego!")
            break
        else:
            print("❌ Opción inválida.")


if __name__ == "__main__":
    menu()
