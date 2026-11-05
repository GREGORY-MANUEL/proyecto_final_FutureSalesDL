"""
SISTEMA DE PROCESAMIENTO DE COMPRAS (GC - PURCHASING TECH)
------------------------------------------------------------
Autor: Gregory Collante
Fecha de Creación: 15 de mayo de 2026
Ubicación: Maracaibo, Zulia, Venezuela
Versión: 3.0 (Arquitectura Modular de Alta Seguridad con RBAC y gctech.db)
"""
import sys
import streamlit as st
import pandas as pd
import datetime
import io
import math
import os
import bcrypt
import re

# Ajuste de ruta para ejecución portable desde PyInstaller one-folder
if getattr(sys, 'frozen', False):
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
#from thefuzz import process, fuzz
from rapidfuzz import process, fuzz

# ── IMPORTACIONES MÓDULOS DE SEGURIDAD INTERNOS ──
import mantenimiento as mt
import login as lg
import registro as rg

# ── IMPORTACIONES NATIVAS DEL MOTOR DE COMPRAS ──
from core.ia_engine import sugerir_cantidades
from core.navigation import obtener_tabs_disponibles
from ui.styles import apply_custom_css, highlight_tendencia, budget_progress_bar

__author__  = "Gregory Collante"
__created__ = "2026-05-15"

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE PÁGINA Y VALIDACIÓN DE INFRAESTRUCTURA
# ─────────────────────────────────────────────
st.set_page_config(page_title="GC - PURCHASING TECH", layout="wide")
apply_custom_css()


def detectar_proveedor_desde_texto(texto_pdf, nombre_archivo=""):
    """Intenta detectar el nombre del proveedor a partir del texto del PDF cargado."""
    if not texto_pdf:
        return None

    # 1. BÚSQUEDA PRIORITARIA: Buscar el patrón "Proveedores : NNNNN-NOMBRE DEL PROVEEDOR"
    # Captura tanto la variante con guion/número como el texto directo después de 'Proveedores :'
    match_proveedores = re.search(
        r"Proveedores\s*:\s*(?:\d+[-_])?\s*([A-ZÁÉÍÓÚÑ0-9&./() \-,]{2,80})",
        texto_pdf,
        re.IGNORECASE,
    )
    if match_proveedores:
        candidato = match_proveedores.group(1).strip()
        # Limpieza de salto de línea o información extra al final del encabezado
        candidato = re.split(r"(\r?\n|Moneda|Fecha|Hora|Pág)", candidato, flags=re.IGNORECASE)[0].strip()
        if candidato and candidato.upper() != "PROVEEDOR":
            return candidato.upper()

    # 2. BÚSQUEDA SECUNDARIA: Patrón genérico 'PROVEEDOR:'
    match_generico = re.search(r"PROVEEDOR(?:\s*[:\-])?\s*([A-ZÁÉÍÓÚÑ0-9&./() \-,]{2,60})", texto_pdf, re.IGNORECASE)
    if match_generico:
        candidato = re.sub(r"\s+", " ", match_generico.group(1)).strip()
        if candidato and candidato.upper() != "PROVEEDOR":
            return candidato.upper()

    # 3. BÚSQUEDA POR PALABRAS CLAVE DE PROVEEDORES CONOCIDOS
    texto = re.sub(r"\s+", " ", texto_pdf).strip().upper()
    proveedores = [
        ("ARTZIO S.A.", ["ARTZIO"]),
        ("MMC - LYNOX", ["MMC", "LYNOX", "PRECIO BASE", "PRECIO 2"]),
        ("3W", ["3W", "THINKS"]),
        ("DISTRIGAMA", ["DISTRIGAMA", "UNIDAD MIN"]),
        ("FERRE X", ["FAGUAX", "FERRE X", "FERREX", "GRIFERIA"]),
        ("EXCELINE", ["EXCELINE", "MEJOR PRECIO REFERENCIAL"]),
        ("FERMETAL", ["FERMETAL", "JAPPY", "SUNICO"]),
        ("TEPLICE", ["TEPLICE", "INDUMA", "PV X CAJA"]),
        ("ABRACOL", ["ABRACOL", "LIJA DE AGUA"]),
        ("BARI", ["BARI", "HERRAJES BARI"]),
        ("TOTAL", ["TOTAL TOOLS", "TOTALTOOLS"]),
        ("A&G", ["FERRE MATERIALES", "FERREMATERIALES", "PAGO 21 DIAS"]),
        ("MAXCAM", ["MAXCAM", "MAXCAN", "PRECIO UNIDAD"]),
        ("BELL POWER", ["BELL POWER", "BELLPOWER"]),
        ("BELL POWER MANG", ["MANGUERAS PVC", "MANGUERA PVC"]),
        ("SAER", ["SAER", "CHINT", "NXB-125"]),
        ("VONANMAX", ["VONANMAX", "FER-"]),
        ("DIS-MEGA", ["DISTRIBUCIONES MEGA", "DIS-MEGA", "MEGA"]),
        ("VENCERAMICA", ["VENCERAMICA", "PVENTA DISTRIBUIDOR"]),
        ("VENCERAMICA W.C", ["VENCERAMICA", "PVENTA BLANCO", "SANITARIOS"]),
        ("FERRO NORTE HOME C.A.", ["FERRO NORTE", "FERRO-NORTE"]),
    ]

    for nombre_prov, keywords in proveedores:
        if any(kw.upper() in texto for kw in keywords):
            return nombre_prov

    # 4. BÚSQUEDA POR NOMBRE DE ARCHIVO
    if nombre_archivo:
        nombre_arch = nombre_archivo.lower().replace("_", " ").replace("-", " ")
        for nombre_prov, palabras in [
            ("ARTZIO S.A.", ["artzio"]),
            ("MMC - LYNOX", ["mmc", "lynox"]),
            ("3W", ["3w", "thinks"]),
            ("DISTRIGAMA", ["distrigama"]),
            ("FERRE X", ["faguax", "ferre x", "ferrex"]),
            ("EXCELINE", ["exceline"]),
            ("FERMETAL", ["fermetal", "jappy", "sunico"]),
            ("TEPLICE", ["teplice", "induma"]),
            ("ABRACOL", ["abracol"]),
            ("BARI", ["bari", "herrajes"]),
            ("TOTAL", ["total tools", "totaltools", "total_tools"]),
            ("A&G", ["a&g", "ferre materiales", "ferremateriales"]),
            ("MAXCAM", ["maxcam", "maxcan"]),
            ("BELL POWER", ["bell power", "bellpower", "bell_power"]),
            ("BELL POWER MANG", ["mangueras", "manguera pvc"]),
            ("SAER", ["saer", "chint", "saer_chint"]),
            ("VONANMAX", ["vonanmax", "vonan max"]),
            ("DIS-MEGA", ["mega", "dis-mega", "dis_mega"]),
            ("VENCERAMICA", ["venceramica ferreteria", "venceramica_ferreteria"]),
            ("VENCERAMICA W.C", ["venceramica wc", "venceramica_wc"]),
            ("FERRO NORTE HOME C.A.", ["ferro norte", "ferro-norte", "ferronorte"]),
        ]:
            if any(pal in nombre_arch for pal in palabras):
                return nombre_prov

    return None


def inicializar_sistema():
    """Garantiza la creación de las tablas de seguridad y compras en gctech.db"""
    mt.inicializar_base_datos()
    conn = mt.conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM usuarios")
    if cursor.fetchone()[0] == 0:
        admin_pass = bcrypt.hashpw(b"admin123", bcrypt.gensalt()).decode('utf-8')
        cursor.execute("INSERT INTO usuarios (username, password_hash, rol, estado, fecha_expiracion) VALUES (?, ?, ?, 'activo', NULL)", ("admin", admin_pass, "administrador"))
        conn.commit()
    conn.close()

# Inicialización obligatoria
inicializar_sistema()

# Middleware de Autorización Basada en Roles (RBAC)
def tiene_permiso(modulo_requerido):
    if not st.session_state.get("logged_in", False):
        return False
        
    # Obtener el rol del usuario logueado desde la sesión
    rol = st.session_state.get("rol", None)
    
    # 1. Administrador siempre tiene acceso
    if rol == "administrador":
        return True
    
    # Soporte para la lógica anterior (listas de permisos)
    if isinstance(modulo_requerido, list):
        return rol in modulo_requerido
    
    return False

# ─────────────────────────────────────────────
# ESTADOS DE SESIÓN REQUERIDOS POR EL MOTOR
# ─────────────────────────────────────────────
if "df_datos"       not in st.session_state: st.session_state["df_datos"]       = pd.DataFrame()
if "last_file_id"   not in st.session_state: st.session_state["last_file_id"]   = None
if "audit_logs"     not in st.session_state: st.session_state["audit_logs"]     = []
if "last_cat_id"    not in st.session_state: st.session_state["last_cat_id"]    = None
if "cat_lines"      not in st.session_state: st.session_state["cat_lines"]      = []
if "cat_proveedor"  not in st.session_state: st.session_state["cat_proveedor"]  = None
if "dict_cat"       not in st.session_state: st.session_state["dict_cat"]       = {}
if "nuevos_cods"    not in st.session_state: st.session_state["nuevos_cods"]    = []
if "matched_count"  not in st.session_state: st.session_state["matched_count"]  = 0
if "mostrar_exito"  not in st.session_state: st.session_state["mostrar_exito"]  = False

# ─────────────────────────────────────────────
# MÓDULO OPERATIVO CENTRAL (COMPRAS)
# ─────────────────────────────────────────────
def modulo_compras():
    import numpy as np
    from core.finance import get_market_rates
    from core.extractors import extraer_datos_a2, extraer_precios_excel, clean_str
    from core.catalogo import (
        extraer_precios_catalogo,
        guardar_perfil_custom,
        eliminar_perfil_custom,
        probar_patron,
        _cargar_perfiles_custom,
    )

    if not tiene_permiso(["usuario"]):
        mt.registrar_log(st.session_state.username, "acceso_denegado", "compras")
        st.error("No tienes autorización para este módulo.")
        return

    # Sidebar — Logo y datos de la aplicación
    try: st.sidebar.image("assets/icono_personal.png")
    except: pass
    st.sidebar.title("GC - Tech")
    st.sidebar.markdown("---")
    st.sidebar.caption(f"✍️ Desarrollado por: {__author__} \n📅 {__created__} · Maracaibo, Venezuela")

    st.title("🛒 Generador de Ordenes de Compras Inteligentes")

    placeholder_parametros = st.container()

    if "nombre_proveedor" not in st.session_state:
        st.session_state["nombre_proveedor"] = st.session_state.get("nombre_proveedor_auto", "")
    if "nombre_proveedor_auto" not in st.session_state:
        st.session_state["nombre_proveedor_auto"] = st.session_state.get("nombre_proveedor", "")

    # Carga de Documentos
    st.divider()
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        uploaded_file = st.file_uploader("1️⃣ Inventario (PDF Formato A2)", type=["pdf"], key="inv_file")
    with col_f2:
        catalogo_file = st.file_uploader("2️⃣ Catálogo / Lista de Precios (PDF o Excel)", type=["pdf", "xlsx", "xls"], key="cat_file")

    if uploaded_file:
        file_bytes = uploaded_file.read()
        try:
            import pdfplumber as _pdfplumber
            stream = io.BytesIO(file_bytes)
            with _pdfplumber.open(stream) as _pdf:
                texto_pdf = "\n".join(page.extract_text() or "" for page in _pdf.pages)

            detected = detectar_proveedor_desde_texto(texto_pdf, uploaded_file.name)
            if not detected:
                detected = uploaded_file.name.replace('.pdf', '').strip().upper()

            prev = st.session_state.get("nombre_proveedor", "")
            if detected and (not prev or prev in ("Proveedor S.A.", "Genérico", "") or prev != detected):
                st.session_state["nombre_proveedor"] = detected
                st.session_state["nombre_proveedor_auto"] = detected
        except Exception:
            pass

    # Layout de Parámetros Globales (renderizado en el contenedor superior)
    with placeholder_parametros:
        col_p1, col_p2, col_p3, col_p4 = st.columns(4)
        with col_p1:
            nombre_proveedor = st.text_input(
                "Nombre del Proveedor",
                key="nombre_proveedor",
                placeholder="Proveedor S.A.",
            )
        with col_p2:
            stock_min = st.number_input("Pedir si existencia es menor a (Stock Mín):", value=5)
        with col_p3:
            pedir_hasta = st.number_input("Completar stock óptimo hasta (Pedir Hasta):", value=15)
        with col_p4:
            rates = get_market_rates()
            if rates['bcv'] > 0:
                tasa_cambio = rates['bcv']
                st.info(f"Tasa Aplicada (BCV): {tasa_cambio:,.2f} BS")
            else:
                tasa_cambio = st.number_input("Tasa manual (BS/USD)", min_value=1.0, value=50.0)

    # Parámetros Financieros en la Barra Lateral Dinámica
    st.sidebar.subheader("💰 Parámetros Financieros")
    presupuesto_limite = st.sidebar.number_input("Tope Presupuestario Ajustado (USD):", min_value=0.0, value=1000.0, step=50.0)
    aplicar_filtro = st.sidebar.checkbox("📦 Alertar si excede presupuesto", value=True)
    
    st.sidebar.divider()
    descuento1 = st.sidebar.number_input("% Descuento Inicial Ítems Críticos (🔴)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    descuento2 = st.sidebar.number_input("% Descuento Secundario Escalón (🔴)", min_value=0.0, max_value=100.0, value=0.0, step=1.0)
    
    st.sidebar.divider()
    rates_sidebar = get_market_rates()
    if rates_sidebar['bcv'] > 0:
        st.sidebar.markdown(f"""
        <div style="font-size: 0.85em; background: #ffffff; padding: 10px; border-radius: 8px; border: 1px solid #ced4da; margin-bottom: 15px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);">
            <b>💱 Tasas de Cambio</b><br>
            <b>BCV Oficial:</b> {rates_sidebar['bcv']:,.2f} Bs<br>
            <b>Binance:</b> {rates_sidebar['binance']:,.2f} Bs<br>
            <b>Brecha Cambiaria:</b> {rates_sidebar['gap']:.2f}%
        </div>
        """, unsafe_allow_html=True)

    filtro_marca = st.sidebar.text_input("Filtrar visualmente por Descripción / Referencia:", value="")
    fuzzy_mode = st.sidebar.checkbox("⚡ Habilitar Inteligencia Fuzzy", value=False)

    # Inyección de Lógica de Carga de Inventario
    if uploaded_file:
        file_id = f"{uploaded_file.name}_{uploaded_file.size}"
        if st.session_state["last_file_id"] != file_id:
            with st.spinner("Procesando inventario..."):
                # Leemos los bytes una vez para poder inspeccionar la cabecera
                file_bytes = uploaded_file.read()

                # Detectar el proveedor automáticamente desde el contenido del PDF
                try:
                    import pdfplumber as _pdfplumber
                    stream = io.BytesIO(file_bytes)
                    with _pdfplumber.open(stream) as _pdf:
                        texto_pdf = "\n".join(page.extract_text() or "" for page in _pdf.pages)

                    detected = detectar_proveedor_desde_texto(texto_pdf, uploaded_file.name)
                    if not detected:
                        detected = uploaded_file.name.replace('.pdf', '').strip().upper()

                    # Solo sobrescribimos si el usuario no ha cambiado el valor
                    curr = st.session_state.get("nombre_proveedor", "")
                    if detected and (not curr or curr in ("Proveedor S.A.", "Genérico", "")):
                        st.session_state["nombre_proveedor"] = detected
                        st.session_state["nombre_proveedor_auto"] = detected
                    # ── VERIFICACIÓN DE DEUDA CRUZADA (Crédito y Cobranza) ──
                    nombre_a_verificar = detected or st.session_state.get("nombre_proveedor", "")
                    if nombre_a_verificar:
                        try:
                            _cant, _total = mt.verificar_deuda_proveedor(nombre_a_verificar.strip())
                            st.session_state["_deuda_alerta"] = (_cant, _total, nombre_a_verificar) if _cant > 0 else None
                        except Exception:
                            pass
                except Exception:
                    # No rompemos el flujo por errores de lectura del PDF
                    pass

                # Extraemos el inventario usando una copia en memoria (BytesIO)
                try:
                    df_nuevo = extraer_datos_a2(io.BytesIO(file_bytes))
                except Exception:
                    # Fallback a la API anterior si la función esperaba el objeto original
                    try:
                        uploaded_file.seek(0)
                    except Exception:
                        pass
                    df_nuevo = extraer_datos_a2(uploaded_file)

                df_nuevo["Tendencia"] = ""
                df_nuevo["Min_Venta"] = 1.0
                st.session_state["df_datos"] = df_nuevo
                st.session_state["last_file_id"] = file_id
                st.session_state["last_cat_id"] = None
            # Forzar re-render para que el input del proveedor muestre el valor detectado
            try:
                st.rerun()
            except Exception:
                # Si rerun falla en este entorno, mostramos el toast y continuamos
                st.toast(f"✅ Inventario cargado: {len(df_nuevo)} productos")

    # Procesamiento Inteligente del Catálogo Externo
    if catalogo_file and not st.session_state["df_datos"].empty:
        cat_id = f"cat_{catalogo_file.name}_{catalogo_file.size}"
        
        if st.session_state["last_cat_id"] != cat_id:
            with st.spinner("Extrayendo precios del catálogo..."):
                if catalogo_file.name.lower().endswith(('.xlsx', '.xls')):
                    dict_cat = extraer_precios_excel(catalogo_file, tasa_cambio)
                    proveedor_nombre = "Excel"
                    lineas_muestra = []
                else:
                    file_bytes = catalogo_file.read()
                    dict_cat, proveedor_nombre, lineas_muestra = extraer_precios_catalogo(
                        io.BytesIO(file_bytes), catalogo_file.name, tasa_cambio
                    )
                    proveedor_nombre = proveedor_nombre or "Genérico"

            st.session_state["cat_lines"] = lineas_muestra if not catalogo_file.name.lower().endswith(('.xlsx','.xls')) else []
            st.session_state["cat_proveedor"] = proveedor_nombre

            if not dict_cat:
                st.session_state["dict_cat"] = {}
                st.session_state["nuevos_cods"] = []
                st.session_state["matched_count"] = 0
                st.session_state["mostrar_exito"] = False
                st.session_state["last_cat_id"] = cat_id
                st.warning("⚠️ No se encontraron precios en el catálogo.")
                st.rerun()
            else:
                # Convertir todas las claves de dict_cat a mayúsculas para evitar problemas de casing
                dict_cat = {str(k).strip().upper(): v for k, v in dict_cat.items() if k}

                mapa = {}
                for k, v in dict_cat.items():
                    k_str = str(k).strip().upper()
                    ref_str = str(v.get('referencia', '')).strip().upper()
                    
                    # Generar claves estándar
                    claves_proveedor = {k_str, k_str.lstrip('0'), ref_str, ref_str.lstrip('0')}
                    
                    # Generar claves ultra-limpias (sin caracteres especiales como guiones o puntos)
                    for c in list(claves_proveedor):
                        if c:
                            c_clean = re.sub(r'[^A-Z0-9]', '', c)
                            if c_clean:
                                claves_proveedor.add(c_clean)
                                
                    for clave in claves_proveedor:
                        if clave and clave not in mapa:
                            mapa[clave] = v

                df_current = st.session_state["df_datos"].copy()
                precios_anteriores = df_current["Precio Unitario"].astype(float).copy()

                # Normalizar a mayúsculas las referencias e identificadores del inventario
                refs = df_current["Referencia"].astype(str).str.strip().str.upper()
                cods = df_current["Código"].astype(str).str.strip().str.upper()
                
                # Crear versiones ultra-limpias de las referencias e identificadores del inventario
                refs_clean = refs.str.replace(r'[^A-Z0-9]', '', regex=True)
                cods_clean = cods.str.replace(r'[^A-Z0-9]', '', regex=True)

                res_p = (
                    refs.map(mapa, na_action='ignore')
                    .combine_first(refs.str.lstrip('0').map(mapa, na_action='ignore'))
                    .combine_first(refs_clean.map(mapa, na_action='ignore'))
                    .combine_first(cods.map(mapa, na_action='ignore'))
                    .combine_first(cods.str.lstrip('0').map(mapa, na_action='ignore'))
                    .combine_first(cods_clean.map(mapa, na_action='ignore'))
                )

                precio_nuevo_series = res_p.apply(lambda x: float(x['precio']) if isinstance(x, dict) and x.get('precio', 0) > 0 else None)
                min_venta_series = res_p.apply(lambda x: float(x.get('min_venta', 1.0)) if isinstance(x, dict) else None)

                if "Tendencia" not in df_current.columns:
                    df_current["Tendencia"] = ""

                mask_match = precio_nuevo_series.notna()
                df_current.loc[mask_match, "Precio Unitario"] = precio_nuevo_series[mask_match]
                df_current.loc[mask_match, "Min_Venta"] = min_venta_series[mask_match].fillna(1.0)

                if fuzzy_mode:
                    clean_keys_map = {clean_str(k): k for k in mapa.keys() if clean_str(k)}
                    clean_keys_list = list(clean_keys_map.keys())
                    sin_match = df_current[~mask_match].index

                    if len(sin_match) > 0:
                        with st.status("🔍 Fuzzy Matching...", expanded=False) as status_box:
                            fuzzy_cache = {}
                            for idx in sin_match:
                                r_clean = clean_str(df_current.at[idx, "Referencia"])
                                c_clean = clean_str(df_current.at[idx, "Código"])
                                buscar = r_clean if len(r_clean) > 3 else c_clean
                                if not buscar or len(buscar) <= 3: continue
                                if buscar not in fuzzy_cache:
                                    result = process.extractOne(buscar, clean_keys_list, scorer=fuzz.ratio)
                                    best, score, _idx = result if result else (None, 0, None)
                                    fuzzy_cache[buscar] = mapa[clean_keys_map[best]] if score >= 90 else None
                                match_data = fuzzy_cache[buscar]
                                if match_data and match_data.get('precio', 0) > 0:
                                    df_current.at[idx, "Precio Unitario"] = float(match_data['precio'])
                                    df_current.at[idx, "Min_Venta"] = float(match_data.get('min_venta', 1.0))
                                    mask_match.at[idx] = True
                            status_box.update(label="✅ Fuzzy completado", state="complete")

                nuevos_precios = df_current["Precio Unitario"].astype(float)
                mask_cambio = mask_match & (nuevos_precios != precios_anteriores)

                condiciones = [
                    (precios_anteriores == 0) & mask_cambio,
                    (nuevos_precios > precios_anteriores * 1.10) & mask_cambio,
                    (nuevos_precios > precios_anteriores) & mask_cambio,
                    (nuevos_precios < precios_anteriores) & mask_cambio,
                ]
                opciones = ["🟢 Nuevo Precio", "🔴 Subió (>10%)", "⚠️ Subió leve", "🟢 Bajó"]
                df_current["Tendencia"] = np.select(condiciones, opciones, default=df_current["Tendencia"])
                df_current.loc[mask_match & ~mask_cambio & (df_current["Tendencia"] == ""), "Tendencia"] = "✅ Sin cambio"

                df_cambios = df_current[mask_cambio]
                logs = [f"• **{row['Descripción']}**: ${precios_anteriores[idx]:.2f} → ${row['Precio Unitario']:.2f}" for idx, row in df_cambios.iterrows()]

                cods_cat = set(str(k).strip().upper() for k in dict_cat.keys() if k)
                cods_inv = set(df_current["Código"].astype(str).str.strip().str.upper().unique())
                refs_inv = set(df_current["Referencia"].astype(str).str.strip().str.upper().unique())
                nuevos_cods = list(cods_cat - cods_inv - refs_inv)

                st.session_state["df_datos"] = df_current
                st.session_state["audit_logs"] = logs
                st.session_state["dict_cat"] = dict_cat
                st.session_state["nuevos_cods"] = nuevos_cods
                st.session_state["matched_count"] = len(logs)
                st.session_state["mostrar_exito"] = True
                st.session_state["last_cat_id"] = cat_id
                st.rerun()

        # Renderizado persistente de resultados del Catálogo
        if st.session_state.get("mostrar_exito"):
            st.info(f"🏭 Catálogo: **{st.session_state.get('cat_proveedor', 'Genérico')}** · {len(st.session_state.get('dict_cat', {}))} ítems cargados.")
            
            # Sub-módulo de Inyección de Productos Nuevos
            nuevos_cods = st.session_state.get("nuevos_cods", [])
            if nuevos_cods:
                st.subheader(f"✨ Artículos Nuevos Detectados ({len(nuevos_cods)})")
                lista_nuevos = []
                for cd in nuevos_cods:
                    info = st.session_state["dict_cat"].get(cd, {})
                    lista_nuevos.append({
                        "Código": cd,
                        "Referencia": info.get("referencia", cd),
                        "Descripción": str(info.get("descripcion", "PRODUCTO NUEVO")).upper(),
                        "Existencia Real": 0,
                        "Precio Unitario": float(info.get("precio", 0.0)),
                        "Tendencia": "🟢 NUEVO",
                        "Min_Venta": float(info.get("min_venta", 1.0))
                    })
                df_nuevos = pd.DataFrame(lista_nuevos)
                
                with st.expander("👀 Ver e Inyectar productos nuevos", expanded=False):
                    with st.popover("🔍", help="Haga clic para buscar artículos nuevos en el catálogo"):
                        search_new = st.text_input("Buscar por Código, Referencia o Descripción:", key="search_new_items", placeholder="Escriba aquí...")
                    
                    if "selected_new_items" not in st.session_state:
                        st.session_state["selected_new_items"] = []

                    df_editor_base = df_nuevos[["Código", "Referencia", "Descripción", "Precio Unitario"]].copy()
                    df_editor_base.insert(0, "Seleccionar", df_editor_base["Código"].astype(str).apply(lambda cd: cd in st.session_state["selected_new_items"]))

                    if search_new:
                        mask_new = (
                            df_editor_base["Descripción"].str.contains(search_new, case=False, na=False) |
                            df_editor_base["Código"].str.contains(search_new, case=False, na=False) |
                            df_editor_base["Referencia"].str.contains(search_new, case=False, na=False)
                        )
                        df_editor_base = df_editor_base[mask_new]

                    edited_df = st.data_editor(df_editor_base, use_container_width=True, hide_index=True, key="new_items_editor")

                    if edited_df is not None:
                        visible_selected = set(edited_df.loc[edited_df["Seleccionar"] == True, "Código"].astype(str).tolist())
                        visible_codes = set(edited_df["Código"].astype(str).tolist())
                        selected_items = set(st.session_state["selected_new_items"])
                        for code in visible_codes:
                            if code in visible_selected:
                                selected_items.add(code)
                            else:
                                selected_items.discard(code)
                        st.session_state["selected_new_items"] = sorted(selected_items)

                selected_df = df_nuevos[df_nuevos["Código"].astype(str).isin(st.session_state.get("selected_new_items", []))].copy()
                num_selected = len(selected_df)
                btn_lbl = f"🚀 Inyectar Seleccionados ({num_selected})" if num_selected > 0 else "Selecciona productos"
                
                if st.button(btn_lbl, type="primary", disabled=(num_selected == 0)):
                    selected_codes = set(selected_df["Código"].astype(str).tolist())
                    df_to_inject = df_nuevos[df_nuevos["Código"].astype(str).isin(selected_codes)].copy()
                    
                    # Evitar duplicaciones estructurales
                    if "Unidad" in df_to_inject.columns:
                        df_to_inject = df_to_inject.drop(columns=["Unidad"])
                        
                    st.session_state["df_datos"] = pd.concat([st.session_state["df_datos"], df_to_inject], ignore_index=True)
                    st.session_state["nuevos_cods"] = [c for c in nuevos_cods if str(c) not in selected_codes]
                    st.success(f"¡{len(df_to_inject)} productos inyectados!")
                    st.rerun()

    # Constructor Regex de Perfiles de Catálogo (Preservado)
    if catalogo_file and st.session_state.get("cat_lines"):
        proveedor_actual = st.session_state.get("cat_proveedor", "Genérico")
        perfiles_guardados = _cargar_perfiles_custom()
        if proveedor_actual in (None, "Genérico") or proveedor_actual in perfiles_guardados:
            with st.expander("🔧 Configurar Estructura Regex del Proveedor", expanded=False):
                p_patron = st.text_area("Regex pattern", r"(?P<codigo>[A-Z0-9\-]+)\s+(?P<descripcion>.+?)\s+(?P<precio>[\d\.,]+)\s*$")
                if st.button("🔍 Probar Regex"):
                    res = probar_patron(st.session_state["cat_lines"], p_patron)
                    st.write(res[:5] if res else "Sin coincidencias")

    # ─────────────────────────────────────────────
    # MOTOR DE PROPUESTA DE COMPRA (CORREGIDO DE FORMA UNIDIMENSIONAL)
    # ─────────────────────────────────────────────
    if not st.session_state["df_datos"].empty:
        df_full = st.session_state["df_datos"].copy()

        mask_pedido = df_full["Existencia Real"].astype(float) < float(stock_min)
        if filtro_marca:
            mask_marca = (
                df_full["Descripción"].str.contains(filtro_marca, case=False, na=False) |
                df_full["Referencia"].str.contains(filtro_marca, case=False, na=False)
            )
            mask_pedido = mask_pedido & mask_marca

        df_pedido = df_full[mask_pedido].copy()

        # Corrección definitiva del ValueError en .apply
        def calcular_pedido(row):
            try: ex_real = float(row["Existencia Real"])
            except: ex_real = 0.0
            necesario = float(pedir_hasta) - ex_real
            
            mv_val = row.get("Min_Venta")
            if isinstance(mv_val, pd.Series): mv_val = mv_val.iloc[0]
            
            try: mv = float(mv_val or 1.0)
            except: mv = 1.0
                
            if necesario <= 0: return float(0.0)
            return float(math.ceil(necesario / mv) * mv)

        if not df_pedido.empty:
            valores_calculados = [calcular_pedido(row) for _, row in df_pedido.iterrows()]
            df_pedido["Cantidad a Pedir"] = pd.Series(valores_calculados, index=df_pedido.index).astype(float)
        else:
            df_pedido["Cantidad a Pedir"] = 0.0

        df_pedido["Sugerencia IA"] = 0
        for idx, row in df_pedido.iterrows():
            codigo = str(row.get("Código", "")).strip()
            if not codigo:
                continue
            try:
                ex_real = float(row.get("Existencia Real", 0) or 0.0)
            except Exception:
                ex_real = 0.0
            df_pedido.at[idx, "Sugerencia IA"] = int(max(0, sugerir_cantidades(codigo, ex_real)))

        mask_sugerencia = (df_pedido["Cantidad a Pedir"].fillna(0.0) <= 0) & (df_pedido["Sugerencia IA"].fillna(0) > 0)
        df_pedido.loc[mask_sugerencia, "Cantidad a Pedir"] = df_pedido.loc[mask_sugerencia, "Sugerencia IA"]

        if aplicar_filtro and presupuesto_limite > 0 and not df_pedido.empty:
            df_pedido = df_pedido.sort_values(by="Existencia Real", ascending=True).copy()
            for col_num in ["Cantidad a Pedir", "Precio Unitario"]:
                df_pedido[col_num] = pd.to_numeric(df_pedido[col_num], errors="coerce").fillna(0.0)
            
            df_pedido["temp_subtotal"] = df_pedido["Cantidad a Pedir"] * df_pedido["Precio Unitario"]
            df_pedido["cum_sum"] = df_pedido["temp_subtotal"].cumsum()
            df_pedido["Aprobar"] = df_pedido["cum_sum"] <= presupuesto_limite
            df_pedido = df_pedido.drop(columns=["temp_subtotal", "cum_sum"], errors="ignore")
        else:
            df_pedido["Aprobar"] = True

        columnas_a_remover = ["min_venta", "Min_Venta", "Mín. Venta", "Mín Venta", "Unidad", "unidad"]
        df_pedido = df_pedido.drop(columns=[col for col in columnas_a_remover if col in df_pedido.columns], errors="ignore")

        # Configuración estricta del orden de columnas requerido
        columnas_base = ["Aprobar", "Código", "Referencia", "Descripción", "Existencia Real", "Cantidad a Pedir", "Sugerencia IA", "Precio Unitario", "Tendencia", "Sub-total"]
        columnas_finales = [col for col in columnas_base if col in df_pedido.columns]
        columnas_finales += [col for col in df_pedido.columns if col not in columnas_finales]
        df_pedido = df_pedido[columnas_finales]

        st.subheader(f"📋 Propuesta de Pedido — {nombre_proveedor}")

        df_excluidos_inicial = df_pedido[df_pedido["Aprobar"] == False]
        items_desmarcados = len(df_excluidos_inicial)

        if items_desmarcados > 0:
            monto_excluido_usd = (df_excluidos_inicial["Cantidad a Pedir"] * df_excluidos_inicial["Precio Unitario"]).sum()
            presupuesto_total_necesario = presupuesto_limite + monto_excluido_usd
            st.error(
                f"🚨 **Presupuesto Satisfecho al Límite** \n"
                f"Se han desmarcado automáticamente **{items_desmarcados} artículos** por exceder el tope financiero de **${presupuesto_limite:,.2f} USD**.  \n\n"
                f"📈 **Análisis de Lista de Espera:** \n"
                f"* **Valor total de ítems excluidos:** ${monto_excluido_usd:,.2f} USD  \n"
                f"* **Presupuesto exacto sugerido:** **${presupuesto_total_necesario:,.2f} USD**"
            )
        else:
            st.success(f"✅ **Presupuesto Óptimo:** Todos los ítems entran perfectamente en el límite asignado.")

        columnas_bloqueadas = [col for col in df_pedido.columns if col not in ["Aprobar", "Cantidad a Pedir", "Referencia"]]

        st.caption("💡 **Tip de limpieza:** Para excluir un producto de la orden puedes desmarcar '🛒 Aprobar'. Si deseas **eliminarlo visualmente por completo**, haz clic en el número de fila (columna gris izquierda) y presiona el icono de papelera arriba a la derecha (o la tecla 'Suprimir').")

        with st.popover("🔍", help="Haga clic para buscar productos dentro de la propuesta de pedido"):
            search_pedido = st.text_input("Buscar por Código, Referencia o Descripción:", key="search_pedido_local", placeholder="Escriba aquí...")

        if search_pedido:
            mask_ped = (
                df_pedido["Descripción"].str.contains(search_pedido, case=False, na=False) |
                df_pedido["Código"].str.contains(search_pedido, case=False, na=False) |
                df_pedido["Referencia"].str.contains(search_pedido, case=False, na=False)
            )
            df_pedido = df_pedido[mask_ped]

        df_configurado = st.data_editor(
            df_pedido,
            use_container_width=True,
            hide_index=False,
            num_rows="dynamic",
            column_config={
                "Aprobar": st.column_config.CheckboxColumn("🛒 Aprobar", default=True),
                "Código": st.column_config.TextColumn("Código"),
                "Referencia": st.column_config.TextColumn("Referencia"),
                "Descripción": st.column_config.TextColumn("Descripción"),
                "Existencia Real": st.column_config.NumberColumn("Existencia Real", format="%.2f"),
                "Cantidad a Pedir": st.column_config.NumberColumn("Cantidad a Pedir", format="%.2f"),
                "Sugerencia IA": st.column_config.NumberColumn("Sugerido por IA", format="%.0f"),
                "Precio Unitario": st.column_config.NumberColumn("Precio Unitario", format="$%,.2f"),
                "Tendencia": st.column_config.TextColumn("Tendencia"),
                "Sub-total": st.column_config.NumberColumn("Sub-total", format="$%,.2f"),
            },
            disabled=columnas_bloqueadas,
            key="pedido_main_editor"
        )

        df_configurado["Cantidad a Pedir"] = pd.to_numeric(df_configurado["Cantidad a Pedir"], errors="coerce").fillna(0.0)
        df_configurado["Precio Unitario"] = pd.to_numeric(df_configurado["Precio Unitario"], errors="coerce").fillna(0.0)
        df_configurado["Sub-total"] = df_configurado["Cantidad a Pedir"] * df_configurado["Precio Unitario"]

        df_aprobado_final = df_configurado[df_configurado["Aprobar"] == True].copy()
        df_excluidos_final = df_configurado[df_configurado["Aprobar"] == False].copy()

        subtotal_bruto = float(df_aprobado_final["Sub-total"].sum()) if not df_aprobado_final.empty else 0.0
        
        sub_rojos = 0.0
        sub_otros = subtotal_bruto

        if not df_aprobado_final.empty:
            col_busqueda = "Tendencia" if "Tendencia" in df_aprobado_final.columns else "Descripción"
            mask_rojo = df_aprobado_final[col_busqueda].astype(str).str.contains("🔴", na=False)
            sub_rojos = df_aprobado_final[mask_rojo]["Sub-total"].sum()
            sub_otros = df_aprobado_final[~mask_rojo]["Sub-total"].sum()

        m_desc1 = sub_rojos * (descuento1 / 100.0)
        m_desc2 = (sub_rojos - m_desc1) * (descuento2 / 100.0)
        
        total_usd = (sub_rojos - m_desc1 - m_desc2) + sub_otros
        total_bs = total_usd * tasa_cambio

        st.divider()
        col1, col2 = st.columns(2)
        with col1:
            total_unidades = df_aprobado_final['Cantidad a Pedir'].sum() if not df_aprobado_final.empty else 0
            st.write(f"**Items Aprobados:** {len(df_aprobado_final)} | **Excluidos:** {len(df_excluidos_final)} | **Unidades:** {total_unidades:,.0f}")
            try: budget_progress_bar(total_usd, presupuesto_limite)
            except: st.progress(min(max(total_usd / (presupuesto_limite or 1.0), 0.0), 1.0))
            
        with col2:
            st.write(f"**Sub-total bruto aprobado:** ${subtotal_bruto:,.2f} / **Presupuesto:** ${presupuesto_limite:,.2f}")
            
            if descuento1 > 0 or descuento2 > 0:
                with st.expander("🔍 Ver Desglose de Descuentos (Aplica solo a ítems 🔴)"):
                    st.write(f"- **Sub-total ítems con 🔴:** `${sub_rojos:,.2f}`")
                    st.write(f"- **Sub-total ítems normales (Sin desc.):** `${sub_otros:,.2f}`")
                    st.write(f"- **Descuento 1 ({descuento1}% sobre 🔴):** `-${m_desc1:,.2f}`")
                    st.write(f"- **Descuento 2 ({descuento2}% sobre 🔴 restando D1):** `-${m_desc2:,.2f}`")
                    st.write(f"- **Ahorro Total:** `-${m_desc1 + m_desc2:,.2f}`")
            
            st.subheader(f"💵 Total Neto: ${total_usd:,.2f} | {total_bs:,.2f} Bs")
        
        if aplicar_filtro and presupuesto_limite > 0 and total_usd > presupuesto_limite:
            st.error(f"🚨 **Pedido Excedido por Ajuste Manual** en **${(total_usd - presupuesto_limite):,.2f} USD**.")

        # ─────────────────────────────────────────────
        # EXPORTACIÓN A EXCEL: CARPETA Y SECUENCIA LOCAL
        # ─────────────────────────────────────────────
        import os
        import glob

        if st.button("📥 Generar y Guardar Orden de Compra (Excel)", type="primary", use_container_width=True):
            fecha_hoy = datetime.datetime.now().strftime("%Y-%m-%d")
            for _, row in df_aprobado_final.iterrows():
                try:
                    ex_real = float(row.get("Existencia Real", 0) or 0.0)
                    cant = float(row.get("Cantidad a Pedir", 0) or 0.0)
                except Exception:
                    ex_real = 0.0
                    cant = 0.0
                mt.guardar_registro_pedido(
                    fecha_hoy,
                    str(row.get("Código", "")).strip(),
                    str(row.get("Descripción", "")).strip(),
                    ex_real,
                    cant,
                    nombre_proveedor,
                )

            df_export = df_aprobado_final[["Código", "Referencia", "Descripción", "Existencia Real", "Cantidad a Pedir", "Precio Unitario", "Sub-total"]].copy()
            df_export.reset_index(drop=True, inplace=True)
            
            # Construir la estructura de carpetas local
            base_folder = "orden de compra"
            prov_clean = "".join(c for c in nombre_proveedor if c.isalnum() or c in (' ', '_')).strip().upper()
            if not prov_clean:
                prov_clean = "PROVEEDOR_DESCONOCIDO"
            
            mes_ano = datetime.datetime.now().strftime("%m_%Y")
            target_dir = os.path.join(base_folder, prov_clean, mes_ano)
            os.makedirs(target_dir, exist_ok=True)
            
            # Determinar la secuencia numérica para el nombre de archivo
            existing_files = glob.glob(os.path.join(target_dir, f"OC_{prov_clean}_*.xlsx"))
            next_seq = len(existing_files) + 1
            file_name = f"OC_{prov_clean}_{next_seq:03d}.xlsx"
            file_path = os.path.join(target_dir, file_name)

            # Generar Excel en memoria
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                # startrow=0 para eliminar las 4 filas vacías superiores
                df_export.to_excel(writer, index=False, sheet_name='OrdenCompra', startrow=0)
                workbook = writer.book
                worksheet = writer.sheets['OrdenCompra']
                
                bg_green = '#C6E0B4'
                
                header_fmt = workbook.add_format({'bold': True, 'font_color': '#000000', 'bg_color': bg_green, 'border': 1, 'align': 'center', 'valign': 'vcenter'})
                cell_fmt = workbook.add_format({'border': 1, 'align': 'left', 'valign': 'vcenter'})
                num_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '#,##0.00'})
                money_fmt = workbook.add_format({'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '#,##0.00'})
                qty_fmt = workbook.add_format({'bold': True, 'bg_color': bg_green, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '#,##0.00'})

                worksheet.set_column('A:A', 15)  
                worksheet.set_column('B:B', 20)  
                worksheet.set_column('C:C', 50)  
                worksheet.set_column('D:D', 15)  
                worksheet.set_column('E:E', 18)  
                worksheet.set_column('F:F', 18)  
                worksheet.set_column('G:G', 18)  
                worksheet.set_row(0, 20) # Fila de cabecera en el tope (0)

                for col_idx, text in enumerate(df_export.columns):
                    worksheet.write(0, col_idx, text, header_fmt)

                start_row = 1
                for i, row in df_export.iterrows():
                    current_row = start_row + i
                    worksheet.write(current_row, 0, row["Código"], cell_fmt)
                    worksheet.write(current_row, 1, row["Referencia"], cell_fmt)
                    worksheet.write(current_row, 2, str(row["Descripción"]).upper(), cell_fmt)
                    worksheet.write(current_row, 3, row["Existencia Real"], num_fmt)
                    worksheet.write(current_row, 4, row["Cantidad a Pedir"], qty_fmt)
                    worksheet.write(current_row, 5, row["Precio Unitario"], money_fmt)
                    worksheet.write(current_row, 6, row["Sub-total"], money_fmt)
                    worksheet.set_row(current_row, 18)

                # --- FILA DE TOTALES ---
                last_row = start_row + len(df_export)
                total_bg_left = workbook.add_format({'bold': True, 'bg_color': bg_green, 'border': 1, 'align': 'right', 'valign': 'vcenter'})
                total_bg_qty = workbook.add_format({'bold': True, 'bg_color': bg_green, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '#,##0.00'})
                total_bg_money = workbook.add_format({'bold': True, 'bg_color': bg_green, 'border': 1, 'align': 'center', 'valign': 'vcenter', 'num_format': '#,##0.00'})
                
                worksheet.merge_range(last_row, 2, last_row, 3, "TOTALES:", total_bg_left)
                worksheet.write(last_row, 4, total_unidades, total_bg_qty)
                worksheet.write(last_row, 6, subtotal_bruto, total_bg_money)
                worksheet.set_row(last_row, 18)

                # --- BLOQUE INFERIOR DE PROVEEDOR Y RESUMEN NETO ---
                prov_label = workbook.add_format({'bold': True, 'bg_color': bg_green, 'border': 1, 'align': 'left', 'valign': 'vcenter'})
                
                worksheet.write(last_row + 2, 1, "PROVEEDOR:", prov_label)
                worksheet.merge_range(last_row + 2, 2, last_row + 2, 4, nombre_proveedor.upper(), prov_label)

                fecha_gen = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")
                worksheet.merge_range(last_row + 4, 1, last_row + 4, 4, f"Fecha y Hora de Generación: {fecha_gen}", prov_label)

                lbl_white = workbook.add_format({'bold': True, 'border': 1, 'align': 'left', 'valign': 'vcenter'})
                val_white = workbook.add_format({'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '$#,##0.00'})
                
                lbl_green = workbook.add_format({'bold': True, 'bg_color': bg_green, 'border': 1, 'align': 'left', 'valign': 'vcenter'})
                val_green = workbook.add_format({'bold': True, 'bg_color': bg_green, 'border': 1, 'align': 'right', 'valign': 'vcenter', 'num_format': '#,##0.00" BS"'})

                worksheet.write(last_row + 2, 5, "Sub-total Bruto:", lbl_white)
                worksheet.write(last_row + 2, 6, subtotal_bruto, val_white)
                
                worksheet.write(last_row + 3, 5, "TOTAL NETO (USD):", lbl_white)
                worksheet.write(last_row + 3, 6, total_usd, val_white)
                
                worksheet.write(last_row + 4, 5, "TOTAL NETO (BS):", lbl_green)
                worksheet.write(last_row + 4, 6, total_bs, val_green)

                workbook.set_properties({
                    'title': 'Orden de Compra Inteligente - GC Tech',
                    'author': 'Gregory Collante',
                    'company': 'GC Tech Purchasing'
                })
            
            # Guardar el archivo directamente en el sistema de carpetas local
            with open(file_path, "wb") as f:
                f.write(output.getvalue())
            
            st.success(f"✅ ¡Orden guardada exitosamente!\n\n📁 **Ruta:** `{file_path}`")

        if st.button("🧹 Limpiar Inventario de la Sesión"):
            st.session_state["df_datos"] = pd.DataFrame()
            st.rerun()
    else:
        st.info("👆 Sube un inventario base para procesar la propuesta de pedidos automáticos.")

# ─────────────────────────────────────────────
# MÓDULOS DE RENDERIZADO VISUAL DE INFRAESTRUCTURA
# ─────────────────────────────────────────────
def modulo_auditoria():
    st.title("📋 Registro de Eventos (Auditoría)")
    if not tiene_permiso([]):
        mt.registrar_log(st.session_state.username, "acceso_denegado", "auditoria")
        st.error("No tienes autorización.")
        return
    conn = mt.conectar_db()
    cursor = conn.cursor()
    cursor.execute("SELECT fecha_hora, usuario, accion, modulo, detalles FROM log_auditoria ORDER BY id DESC")
    logs = cursor.fetchall()
    conn.close()
    st.dataframe([dict(log) for log in logs], use_container_width=True)

def modulo_mantenimiento_vista():
    if not tiene_permiso([]):
        mt.registrar_log(st.session_state.username, "acceso_denegado", "mantenimiento")
        st.error("No tienes autorización.")
        return

    col_izq, col_der = st.columns(2)
    with col_izq:
        st.subheader("💾 Respaldos de Seguridad (Backup)")
        if st.button("🚀 Crear Copia de Seguridad Ahora"):
            try:
                ruta_backup = mt.crear_copia_seguridad()
                mt.registrar_log(st.session_state.username, "crear_backup", "mantenimiento", f"Archivo: {ruta_backup}")
                st.success(f"¡Respaldo creado con éxito!: `{ruta_backup}`")
            except Exception as e: st.error(f"Error: {e}")
        
        # Inyección del botón de descarga dinámico apuntando a gctech.db
        if os.path.exists(mt.DB_NAME):
            with open(mt.DB_NAME, "rb") as f:
                st.download_button(
                    "📥 Descargar Base de Datos Actual (.db)", 
                    data=f, 
                    file_name="gctech_live.db", 
                    mime="application/x-sqlite3"
                )

    with col_der:
        st.subheader("🔄 Diagnóstico y Corrección")
        if st.button("🔍 Diagnosticar e Indexar"):
            resultado = mt.ejecutar_diagnostico_y_reindex()
            if resultado == "ok" or resultado is None:
                st.success("✅ Estructura indexada y saludable de gctech.db.")
                mt.registrar_log(st.session_state.username, "diagnostico_db_exitoso", "mantenimiento")
            else:
                st.error(f"⚠️ Alerta estructural: {resultado}")

# ─────────────────────────────────────────────
# MÓDULO DE PREDICCIÓN DE VENTAS (FutureSalesDL)
# ─────────────────────────────────────────────
def modulo_prediccion_ventas():
    """Pantalla completa del módulo FutureSalesDL integrada en el menú principal."""
    from core.procesamiento_historial import procesar_historial_txt
    from generar_historial import (
        cargar_ventas_originales,
        filtrar_dataset_entrenamiento,
        guardar_dataset_entrenamiento,
    )

    st.title("📈 Predicción de Ventas — FutureSalesDL")
    st.markdown(
        "Adjunta un CSV de entrenamiento para usarlo directamente o carga el TXT original "
        "para generar un dataset por período."
    )
    st.divider()

    # ── Panel de configuración ──────────────────────────────────────────────
    with st.expander("⚙️ Parámetros del Modelo", expanded=True):
        col1, col2, col3, col4, col5 = st.columns(5)
        with col1:
            dias_a_predecir = st.number_input("📅 Períodos a predecir", min_value=1, max_value=90, value=7, step=1)
        with col2:
            ventana = st.number_input("🪟 Ventana (períodos)", min_value=7, max_value=60, value=30, step=1)
        with col3:
            epochs = st.number_input("🔄 Épocas", min_value=20, max_value=1000, value=250, step=10)
        with col4:
            batch_size = st.selectbox("📦 Batch size", [8, 16, 32, 64, 128, 256], index=1)
        with col5:
            frecuencia = st.selectbox("⏱️ Frecuencia", ["D", "W"], index=0, format_func=lambda x: "Diaria" if x == "D" else "Semanal")

    # ── Carga de archivo ────────────────────────────────────────────────────
    archivo = st.file_uploader(
        "📂 Dataset de entrenamiento (.csv) o archivo original (.txt)",
        type=["csv", "txt"],
        help=(
            "El CSV debe incluir columnas de fecha y ventas/cantidad. "
            "El TXT original debe incluir FDI_CODIGO, FDI_CANTIDAD y FDI_FECHAOPERACION."
        ),
        key="pred_archivo_original",
    )

    if archivo is None:
        st.info("Adjunta un CSV listo para entrenar o un TXT original para prepararlo.")
        return

    archivo_id = f"{archivo.name}_{archivo.size}"
    es_csv_directo = archivo.name.lower().endswith(".csv")

    if es_csv_directo:
        try:
            df_entrenamiento, _, _, _ = procesar_historial_txt(
                io.BytesIO(archivo.getvalue())
            )
        except ValueError as e:
            st.error(str(e))
            return
        filtro_actual = ("csv", archivo_id)
        st.session_state["pred_dataset_csv"] = archivo.getvalue()
        st.session_state["pred_dataset_df"] = df_entrenamiento
        st.session_state["pred_dataset_filtro"] = filtro_actual
        dataset_generado = True
    else:
        if st.session_state.get("pred_archivo_id") != archivo_id:
            try:
                dataset_base = cargar_ventas_originales(io.BytesIO(archivo.getvalue()))
            except ValueError as e:
                st.error(str(e))
                return
            st.session_state["pred_archivo_id"] = archivo_id
            st.session_state["pred_dataset_base"] = dataset_base
            st.session_state.pop("pred_fecha_inicio", None)
            st.session_state.pop("pred_fecha_fin", None)
            st.session_state.pop("pred_dataset_csv", None)
            st.session_state.pop("pred_dataset_filtro", None)
            st.session_state.pop("pred_resultado", None)

        dataset_base = st.session_state["pred_dataset_base"]
        fecha_min = pd.to_datetime(dataset_base["Fecha"]).min().date()
        fecha_max = pd.to_datetime(dataset_base["Fecha"]).max().date()
        col_fecha_inicio, col_fecha_fin = st.columns(2)
        with col_fecha_inicio:
            fecha_inicio = st.date_input(
                "Fecha de inicio",
                value=fecha_min,
                min_value=fecha_min,
                max_value=fecha_max,
                key="pred_fecha_inicio",
            )
        with col_fecha_fin:
            fecha_fin = st.date_input(
                "Fecha fin",
                value=fecha_max,
                min_value=fecha_min,
                max_value=fecha_max,
                key="pred_fecha_fin",
            )

        filtro_actual = (archivo_id, fecha_inicio.isoformat(), fecha_fin.isoformat())
        if fecha_inicio > fecha_fin:
            st.error("La fecha de inicio debe ser anterior o igual a la fecha fin.")
            return

        if st.button(
            "🧾 Generar dataset_entrenamiento.csv",
            type="primary",
            use_container_width=True,
        ):
            try:
                df_entrenamiento = filtrar_dataset_entrenamiento(
                    dataset_base, fecha_inicio, fecha_fin
                )
                csv_bytes = df_entrenamiento.to_csv(
                    index=False, encoding="utf-8-sig"
                ).encode("utf-8-sig")
                st.session_state["pred_dataset_csv"] = csv_bytes
                st.session_state["pred_dataset_df"] = df_entrenamiento
                st.session_state["pred_dataset_filtro"] = filtro_actual
                st.session_state.pop("pred_resultado", None)
            except ValueError as e:
                st.error(str(e))

        dataset_generado = st.session_state.get("pred_dataset_filtro") == filtro_actual

    if dataset_generado:
        df_entrenamiento = st.session_state["pred_dataset_df"]
        origen = "CSV cargado" if es_csv_directo else "Dataset listo"
        st.success(f"{origen}: {len(df_entrenamiento):,} registros diarios.")
        st.caption(
            "El predictor actual suma las ventas de todos los códigos por fecha; "
            "la proyección representa el total diario, no una predicción por producto."
        )
        directorio_app = (
            os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            if getattr(sys, "frozen", False)
            else os.path.dirname(os.path.abspath(__file__))
        )
        directorio_datasets = os.path.join(
            directorio_app, "archivos", "data2", "datasets_entrenamiento"
        )
        if st.button("💾 Guardar dataset", use_container_width=True):
            try:
                ruta_guardado = guardar_dataset_entrenamiento(
                    st.session_state["pred_dataset_csv"], directorio_datasets
                )
                st.success(f"Dataset guardado en: `{ruta_guardado}`")
            except OSError as error:
                st.error(f"No se pudo guardar el dataset: {error}")
        st.dataframe(df_entrenamiento.head(20), use_container_width=True, hide_index=True)

        if "Promocion_Activa" in df_entrenamiento.columns:
            porcentaje_promocion = float(df_entrenamiento["Promocion_Activa"].mean() * 100)
            st.metric("Registros con promoción activa", f"{porcentaje_promocion:.2f}%")
            st.caption(
                "Se usa la columna Promocion_Activa del archivo cuando está disponible; "
                "si no existe, el parser asigna 0."
            )
        else:
            st.warning(
                "No se puede calcular la probabilidad de promoción: el TXT no contiene "
                "una columna Promocion_Activa. Se necesita una etiqueta real por venta; "
                "las cantidades por sí solas no permiten confirmar una promoción."
            )

    entrenar = st.button(
        "🚀 Entrenar modelo y predecir",
        use_container_width=True,
        disabled=not dataset_generado,
    )
    if entrenar:
        with st.spinner("🤖 Entrenando FutureSalesDL... esto puede tomar unos minutos."):
            try:
                from core.prediccion_ventas import ejecutar_future_sales_dl

                df_pred, metricas, historial_perdida = ejecutar_future_sales_dl(
                    archivo_txt=io.BytesIO(st.session_state["pred_dataset_csv"]),
                    dias_a_predecir=int(dias_a_predecir),
                    epochs=int(epochs),
                    ventana=int(ventana),
                    batch_size=int(batch_size),
                    freq=frecuencia
                )
                st.session_state["pred_resultado"]       = df_pred
                st.session_state["pred_metricas"]        = metricas
                st.session_state["pred_historial"]       = historial_perdida
                st.session_state["pred_dias_predecir"]   = int(dias_a_predecir)
                st.session_state["pred_resultado_filtro"] = filtro_actual
            except ValueError as e:
                st.error(f"❌ {e}")
                return
            except Exception as e:
                st.error(f"❌ Error inesperado: {e}")
                return

    # ── Mostrar resultados si ya se entrenó ─────────────────────────────────
    if (
        "pred_resultado" not in st.session_state
        or st.session_state.get("pred_resultado_filtro") != filtro_actual
    ):
        return

    df_pred          = st.session_state["pred_resultado"]
    metricas         = st.session_state["pred_metricas"]
    historial_perdida = st.session_state["pred_historial"]

    st.success("✅ Modelo entrenado y predicciones generadas.")
    st.divider()

    # ── Tarjetas de métricas ─────────────────────────────────────────────────
    st.subheader("📊 Métricas de Validación (20% cronológico)")
    st.markdown("""
        <style>
        [data-testid="stMetricValue"] {
            font-size: 1.8rem !important;
        }
        </style>
    """, unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📉 RMSE", f"{metricas['RMSE']:,.2f}", help="Error cuadrático medio (unidades reales)")
    m2.metric("📏 MAE",  f"{metricas['MAE']:,.2f}",  help="Error absoluto medio (unidades reales)")
    m3.metric("🎯 WAPE", f"{metricas.get('WAPE', 0):,.2f}%", help="Error Porcentual Absoluto Ponderado")
    m4.metric("📅 Períodos Proyectados", st.session_state["pred_dias_predecir"])

    st.divider()

    # ── Tabla y gráfico de predicciones ─────────────────────────────────────
    col_tabla, col_chart = st.columns([1, 2])

    with col_tabla:
        st.subheader("🗓️ Proyección")
        st.dataframe(
            df_pred.rename(columns={"Fecha": "Fecha", "Predicción de Ventas": "Ventas Proyectadas"}),
            use_container_width=True,
            hide_index=True,
        )

    import plotly.graph_objects as go

    with col_chart:
        st.subheader("📈 Curva de Predicción")
        fig_pred = go.Figure()
        fig_pred.add_trace(go.Scatter(
            x=df_pred["Fecha"],
            y=df_pred["Predicción de Ventas"],
            mode="lines+markers",
            name="Predicción",
            line=dict(color="#4F8EF7", width=2.5),
            marker=dict(size=7, color="#4F8EF7"),
            fill="tozeroy",
            fillcolor="rgba(79,142,247,0.10)",
        ))
        fig_pred.update_layout(
            xaxis_title="Fecha",
            yaxis_title="Ventas",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#FAFAFA"),
            margin=dict(l=10, r=10, t=10, b=10),
            hovermode="x unified",
        )
        st.plotly_chart(fig_pred, use_container_width=True)

    st.divider()

    # ── Curva de aprendizaje (pérdida por epoch) ─────────────────────────────
    st.subheader("📉 Curva de Aprendizaje (Loss por Epoch)")
    fig_loss = go.Figure()
    fig_loss.add_trace(go.Scatter(
        x=list(range(1, len(historial_perdida['train']) + 1)),
        y=historial_perdida['train'],
        mode="lines",
        name="Train Loss (MSE)",
        line=dict(color="#F7854F", width=2),
    ))
    fig_loss.add_trace(go.Scatter(
        x=list(range(1, len(historial_perdida['val']) + 1)),
        y=historial_perdida['val'],
        mode="lines",
        name="Validation Loss (MSE)",
        line=dict(color="#4F8EF7", width=2, dash="dash"),
    ))
    fig_loss.update_layout(
        xaxis_title="Epoch",
        yaxis_title="MSE (objetivo log-transformado y normalizado)",
        plot_bgcolor="rgba(0,0,0,0)",
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#FAFAFA"),
        margin=dict(l=10, r=10, t=10, b=10),
        hovermode="x unified",
    )
    perdidas_graficadas = historial_perdida['train'] + historial_perdida['val']
    fig_loss.update_yaxes(
        type="log" if perdidas_graficadas and all(valor > 0 for valor in perdidas_graficadas) else "linear"
    )
    st.plotly_chart(fig_loss, use_container_width=True)

    # ── Exportar predicciones ────────────────────────────────────────────────
    st.divider()
    csv_export = df_pred.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Descargar Predicciones CSV",
        data=csv_export,
        file_name="predicciones_ventas.csv",
        mime="text/csv",
        use_container_width=True,
    )


# ─────────────────────────────────────────────
# ORQUESTACIÓN DE ACCESO Y MENÚ LATERAL
# ─────────────────────────────────────────────
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    lg.mostrar_login()
else:
    # ── Sidebar con Información de Usuario ──
    st.sidebar.title(f"👤 {st.session_state.get('username', 'USER').upper()}")
    st.sidebar.write(f"Rol Activo: **{st.session_state.get('rol', 'Invitado')}**")
    st.sidebar.divider()

    # ── Definición de Pestañas y Roles ──
    rol = st.session_state.get("rol", "invitado")
    tabs = obtener_tabs_disponibles(rol)
    tab_labels = {
        "Compras": "Compras",
        "Predicción": "Predicción",
        "Administración": "Administración",
        "Auditoría": "Auditoría",
        "Mantenimiento": "Mantenimiento",
    }

    # Validación de página actual
    if "pagina_actual" not in st.session_state or st.session_state.pagina_actual not in tabs:
        st.session_state.pagina_actual = tabs[0]

    # Índice por defecto para el selector
    default_index = tabs.index(st.session_state.pagina_actual)

    # ── Renderizado de Pestañas Superiores (Estilo Nav-Tabs) ──
    st.markdown(
        """
        <style>
        div.stButton > button {
            background: transparent;
            border: none;
            border-bottom: 2px solid transparent;
            color: #2563eb !important;
            padding: 0.5rem 0.5rem;
            font-weight: 600;
            border-radius: 0;
            box-shadow: none;
            margin-bottom: 0.25rem;
            min-width: 120px;
            white-space: normal;
            text-align: center;
            font-size: 0.95rem;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            gap: 0.15rem;
            overflow: visible;
            word-break: break-word;
        }
        div.stButton > button * {
            color: inherit !important;
        }
        div.stButton > button span {
            display: block;
            line-height: 1.05;
            font-size: 0.9rem;
        }
        /* Pestaña activa: subrayado y azul más oscuro */
        div.stButton > button[kind="primary"] {
            color: #1e40af !important;
            border-bottom-color: #1e40af !important;
            background: transparent;
            box-shadow: none;
        }
        /* Hover mantiene azul */
        div.stButton > button:hover {
            color: #1e40af !important;
            border-bottom-color: rgba(30,64,175,0.12) !important;
            background: transparent;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    nav_cols = st.columns(len(tabs))
    for idx, tab in enumerate(tabs):
        with nav_cols[idx]:
            is_active = tab == st.session_state.pagina_actual
            if st.button(
                tab_labels[tab],
                key=f"nav_tab_{tab}",
                use_container_width=True,
                type="primary" if is_active else "secondary",
            ):
                st.session_state.pagina_actual = tab
                st.rerun()

    # ── Botón de Cerrar Sesión en el Sidebar ──
    if st.sidebar.button("Cerrar Sesión", type="primary"):
        mt.registrar_log(st.session_state.get("username"), "logout", "auth")
        st.session_state.clear()
        st.rerun()

    st.divider()

    # ── Enrutador de Módulos ──
    pagina = st.session_state.pagina_actual

    if pagina == "Predicción":
        modulo_prediccion_ventas()
    elif pagina == "Administración":
        rg.mostrar_registro_y_gestion()
    elif pagina == "Auditoría":
        modulo_auditoria()
    elif pagina == "Mantenimiento":
        modulo_mantenimiento_vista()
    else:
        modulo_compras()