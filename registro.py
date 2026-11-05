import streamlit as st
import bcrypt
import sqlite3
import datetime
import mantenimiento as mt

def mostrar_registro_y_gestion():
    st.title("⚙️ Panel de Control de Usuarios")
    conn = mt.conectar_db()
    cursor = conn.cursor()

    st.subheader("➕ Crear Nuevo Operador / Administrador")
    with st.form("crear_usuario_form", clear_on_submit=True):
        new_user = st.text_input("Nombre de Usuario")
        new_pass = st.text_input("Contraseña", type="password")
        new_rol = st.selectbox("Rol del Usuario", ["usuario", "administrador"])
        tiene_limite = st.checkbox("Activar bloqueo automático por fecha límite")
        fecha_limite = st.date_input("Fecha de expiración", min_value=datetime.date.today())
        btn_crear = st.form_submit_button("Registrar Usuario")
        
        if btn_crear:
            if len(new_user.strip()) < 4 or len(new_pass) < 6:
                st.error("Campos inválidos (Usuario min. 4 caracteres, Contraseña min. 6).")
            else:
                try:
                    hash_pass = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                    exp_val = fecha_limite.isoformat() if tiene_limite else None
                    cursor.execute("INSERT INTO usuarios (username, password_hash, rol, estado, fecha_expiracion) VALUES (?, ?, ?, 'activo', ?)", (new_user.strip(), hash_pass, new_rol, exp_val))
                    conn.commit()
                    mt.registrar_log(st.session_state.username, "crear_usuario", "administracion", f"Creado: {new_user}. Expira: {exp_val}")
                    st.success(f"Usuario '{new_user}' registrado exitosamente.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("El nombre de usuario ya existe en el sistema.")

    st.divider()
    st.subheader("👥 Gestión de Usuarios Existentes")
    cursor.execute("SELECT id, username, rol, estado, fecha_expiracion FROM usuarios")
    
    for u in cursor.fetchall():
        es_mismo_usuario = (u["username"] == st.session_state.username)
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        with col1:
            exp_text = f" | ⏳ Expira: `{u['fecha_expiracion']}`" if u["fecha_expiracion"] else " | ♾️ Acceso Indefinido"
            st.write(f"👤 **{u['username']}** ({u['rol']}){exp_text}")
        with col2:
            st.success("🟢 Activo") if u["estado"] == "activo" else st.error("🔴 Bloqueado")
        with col3:
            lbl_accion = "Bloquear" if u["estado"] == "activo" else "Desbloquear"
            if st.button(lbl_accion, key=f"susp_{u['id']}", disabled=es_mismo_usuario):
                nuevo_estado = "suspendido" if u["estado"] == "activo" else "activo"
                cursor.execute("UPDATE usuarios SET estado = ? WHERE id = ?", (nuevo_estado, u["id"]))
                conn.commit()
                mt.registrar_log(st.session_state.username, f"cambiar_estado_{nuevo_estado}", "administracion", f"Usuario: {u['username']}")
                st.rerun()
        with col4:
            if st.button("🗑️ Eliminar", key=f"del_{u['id']}", disabled=es_mismo_usuario):
                cursor.execute("DELETE FROM usuarios WHERE id = ?", (u["id"],))
                conn.commit()
                mt.registrar_log(st.session_state.username, "eliminar_usuario", "administracion", f"Usuario: {u['username']}")
                st.rerun()
    conn.close()