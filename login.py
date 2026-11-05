import streamlit as st
import bcrypt
import mantenimiento as mt

def mostrar_login():
    # Espaciado superior para centrar verticalmente
    st.markdown("<br><br>", unsafe_allow_html=True)
    
    # Columnas para centrar el formulario
    col1, col2, col3 = st.columns([1, 1.2, 1])
    
    with col2:
        st.markdown("<h2 style='text-align: center; color: #1F497D; font-weight: 700; margin-bottom: 5px;'>🔐 GC - Tech</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #666; margin-bottom: 25px; font-size: 1.1em;'>Acceso Protegido al Sistema de Compras</p>", unsafe_allow_html=True)
        
        with st.form("login_form", clear_on_submit=False):
            user_input = st.text_input("👤 Nombre de Usuario", placeholder="Ingresa tu usuario...").strip()
            pass_input = st.text_input("🔑 Contraseña de Acceso", type="password", placeholder="Ingresa tu contraseña...")
            
            st.markdown("<br>", unsafe_allow_html=True)
            btn_ingresar = st.form_submit_button("Ingresar al Sistema", use_container_width=True)
            
            if btn_ingresar:
                if not user_input or not pass_input:
                    st.error("❌ Por favor, rellena todos los campos.")
                    st.stop()

                conn = mt.conectar_db()
                cursor = conn.cursor()
                # Buscamos el usuario de forma limpia e insensible a mayúsculas/minúsculas
                cursor.execute("SELECT password_hash, rol, estado FROM usuarios WHERE LOWER(username) = LOWER(?)", (user_input,))
                user_rec = cursor.fetchone()
                conn.close()
                
                if user_rec:
                    # Comprobación de estado
                    if user_rec["estado"] == "suspendido":
                        st.error("❌ Esta cuenta ha sido suspendida por el administrador.")
                        st.stop()
                    
                    # Convertir datos de la DB a strings/bytes limpios
                    db_hash = user_rec["password_hash"]
                    
                    try:
                        # VALIDACIÓN CRÍTICA BCRYPT
                        if bcrypt.checkpw(pass_input.encode('utf-8'), db_hash.encode('utf-8')):
                            st.session_state.logged_in = True
                            st.session_state.username = user_input
                            st.session_state.rol = user_rec["rol"]
                            
                            mt.registrar_log(user_input, "login_exitoso", "auth")
                            st.success("¡Acceso concedido! Redirigiendo...")
                            st.rerun()
                        else:
                            st.error("❌ Contraseña incorrecta.")
                    except Exception as e:
                        st.error("⚠️ Error en el formato de encriptación de la Base de Datos.")
                        st.info("Es probable que la contraseña esté guardada en texto plano en la DB y Bcrypt no la pueda validar.")
                else:
                    st.error("❌ El usuario no existe en la base de datos.")