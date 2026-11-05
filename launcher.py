"""
Launcher para la aplicacion portable Generador de Ordenes de Compra.
Inicia Streamlit en background y abre una ventana de escritorio con pywebview.
"""
import sys
import os
import threading
import time
import socket

# --- Imports for PyInstaller to trace dependencies ---
if False:
    import streamlit
    import pandas
    import numpy
    import bcrypt
    import rapidfuzz
    import openpyxl
    import xlsxwriter
    import requests
    import pdfplumber
    import mantenimiento
    import login
    import registro
    import core.finance
    import core.extractors
    import core.catalogo
    import ui.styles
    import torch
    import sklearn
# ----------------------------------------------------


def get_base_path():
    """Retorna la ruta base donde están los archivos de la app."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))


def find_free_port():
    """Encuentra un puerto libre en localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        return s.getsockname()[1]


def wait_for_server(port, timeout=90):
    """Espera hasta que el servidor Streamlit responda."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(('localhost', port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError, TimeoutError):
            time.sleep(0.4)
    return False


def run_streamlit(app_path, port):
    """Ejecuta el servidor Streamlit en segundo plano."""
    try:
        # Configurar directorio de datos de Streamlit en una ubicación escribible
        home_dir = os.path.expanduser('~')
        st_home = os.path.join(home_dir, '.streamlit_generadoroc')
        os.makedirs(st_home, exist_ok=True)
        os.environ['STREAMLIT_HOME'] = st_home

        # Ajustar sys.argv para que Streamlit lo lea correctamente
        sys.argv = [
            "streamlit", "run", app_path,
            f"--server.port={port}",
            "--server.headless=true",
            "--server.enableCORS=false",
            "--server.enableXsrfProtection=false",
            "--browser.gatherUsageStats=false",
            "--server.fileWatcherType=none",
            "--global.developmentMode=false",
        ]

        # Monkeypatch signal para evitar ValueError en threads
        import signal
        try:
            signal.signal = lambda *args, **kwargs: None
        except Exception:
            pass

        from streamlit.web import cli as stcli
        stcli.main()
    except Exception as e:
        import traceback
        log_path = os.path.join(os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else os.path.dirname(__file__), "error_log.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            traceback.print_exc(file=f)


def main():
    app_dir = (
        os.path.dirname(sys.executable)
        if getattr(sys, 'frozen', False)
        else os.path.dirname(os.path.abspath(__file__))
    )
    os.chdir(app_dir)
    base_path = get_base_path()
    app_path = os.path.join(base_path, 'app.py')
    port = find_free_port()

    # ── Iniciar Streamlit en un hilo daemon ──────────────────────────────────
    st_thread = threading.Thread(
        target=run_streamlit,
        args=(app_path, port),
        daemon=True
    )
    st_thread.start()

    # ── Esperar a que el servidor esté listo ─────────────────────────────────
    print(f"Iniciando servidor en localhost:{port} ...")
    if not wait_for_server(port, timeout=90):
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Error de inicio",
            "No se pudo iniciar el servidor de la aplicación.\n"
            "Asegúrate de que los antivirus no estén bloqueando el proceso."
        )
        root.destroy()
        sys.exit(1)

    # ── Abrir ventana de escritorio con pywebview ────────────────────────────
    import webview

    window = webview.create_window(
        title='GC - PURCHASING TECH',
        url=f'http://localhost:{port}',
        width=1400,
        height=900,
        min_size=(900, 600),
        resizable=True,
        text_select=True,
    )

    # Intentar con EdgeChromium (Windows 10/11 con WebView2)
    # Si falla, pywebview elige el backend disponible automáticamente
    try:
        webview.start(gui='edgechromium', debug=False)
    except Exception:
        webview.start(debug=False)


if __name__ == '__main__':
    main()
