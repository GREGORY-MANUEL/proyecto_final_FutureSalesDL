import sqlite3
import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_NAME = os.path.join(BASE_DIR, "gctech.db")
BACKUP_DIR = os.path.join(BASE_DIR, "backups")


def conectar_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def asegurar_carpeta_backups():
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)


def inicializar_base_datos():
    conn = conectar_db()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        rol TEXT NOT NULL CHECK(rol IN ('administrador', 'usuario', 'analistaCreditos')),
        estado TEXT NOT NULL DEFAULT 'activo' CHECK(estado IN ('activo', 'suspendido')),
        fecha_expiracion TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS log_auditoria (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha_hora TEXT NOT NULL,
        usuario TEXT,
        accion TEXT NOT NULL,
        modulo TEXT NOT NULL,
        detalles TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historico_pedidos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        fecha TEXT,
        codigo_item TEXT,
        descripcion TEXT,
        existencia_real REAL,
        cantidad_solicitada REAL,
        proveedor TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS control_recepcion (
        id_pedido TEXT PRIMARY KEY,
        proveedor TEXT,
        fecha_pedido TEXT,
        fecha_recepcion_real TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS inventario (
        id INTEGER PRIMARY KEY,
        existencia REAL DEFAULT 0
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS historial_movimientos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        producto_id INTEGER,
        fecha TEXT,
        cantidad REAL,
        tipo TEXT,
        FOREIGN KEY(producto_id) REFERENCES inventario(id)
    )
    """)
    
    conn.commit()
    conn.close()
    asegurar_carpeta_backups()


def registrar_log(usuario, accion, modulo, detalles=""):
    inicializar_base_datos()
    conn = conectar_db()
    cursor = conn.cursor()
    fecha_actual = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute(
        "INSERT INTO log_auditoria (fecha_hora, usuario, accion, modulo, detalles) VALUES (?, ?, ?, ?, ?)",
        (fecha_actual, usuario if usuario else "Anónimo", accion, modulo, detalles)
    )
    conn.commit()
    conn.close()


def guardar_registro_pedido(fecha, codigo, desc, ex_real, cant, prov):
    inicializar_base_datos()
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO historico_pedidos (fecha, codigo_item, descripcion, existencia_real, cantidad_solicitada, proveedor) VALUES (?, ?, ?, ?, ?, ?)",
        (fecha, codigo, desc, ex_real, cant, prov)
    )
    conn.commit()
    conn.close()
    return True


def crear_copia_seguridad():
    asegurar_carpeta_backups()
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"{BACKUP_DIR}/backup_{timestamp}.db"
    conn_actual = conectar_db()
    conn_backup = sqlite3.connect(backup_filename)
    conn_actual.backup(conn_backup)
    conn_backup.close()
    conn_actual.close()
    return backup_filename


def ejecutar_diagnostico_y_reindex():
    conn = conectar_db()
    cursor = conn.cursor()
    cursor.execute("PRAGMA integrity_check")
    row = cursor.fetchone()
    resultado = row[0] if row else "ok"
    cursor.execute("REINDEX")
    conn.commit()
    conn.close()
    return resultado


def compactar_base_datos():
    conn = conectar_db()
    conn.execute("VACUUM")
    conn.close()


def purgar_logs_antiguos(dias):
    conn = conectar_db()
    cursor = conn.cursor()
    fecha_limite = (datetime.datetime.now() - datetime.timedelta(days=dias)).strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("DELETE FROM log_auditoria WHERE fecha_hora < ?", (fecha_limite,))
    filas_afectadas = cursor.rowcount
    conn.commit()
    conn.close()
    return filas_afectadas, fecha_limite


def vaciar_auditoria_completa():
    conn = conectar_db()
    conn.execute("DELETE FROM log_auditoria")
    conn.commit()
    conn.close()


def insertar_datos_prueba_lstm(producto_id=1, existencia=8):
    """
    Inserta datos de prueba en inventario e historial_movimientos
    para poder entrenar y probar el modelo LSTM.
    """
    conn = conectar_db()
    cursor = conn.cursor()
    
    # Inicializar o actualizar existencia del producto
    cursor.execute("INSERT OR REPLACE INTO inventario (id, existencia) VALUES (?, ?)", (producto_id, existencia))
    
    # Verificar si ya existen movimientos
    cursor.execute("SELECT COUNT(*) FROM historial_movimientos WHERE producto_id = ?", (producto_id,))
    count = cursor.fetchone()[0]
    
    if count < 15:
        # Generar 30 días de ventas históricas simuladas
        import random
        base_date = datetime.datetime.now() - datetime.timedelta(days=30)
        # Asegurar un patrón de ventas continuo
        for i in range(30):
            fecha = (base_date + datetime.timedelta(days=i)).strftime("%Y-%m-%d")
            # Ventas de 2 a 8 unidades diarias
            demanda = float(random.randint(2, 8))
            cursor.execute(
                "INSERT INTO historial_movimientos (producto_id, fecha, cantidad, tipo) VALUES (?, ?, ?, ?)",
                (producto_id, fecha, demanda, 'VENTA')
            )
        conn.commit()
        print(f"[INFO] Datos de prueba creados para el Producto ID {producto_id} (30 registros de ventas simuladas).")
    else:
        print(f"[INFO] El Producto ID {producto_id} ya posee {count} registros de historial de movimientos.")
        
    conn.close()


if __name__ == '__main__':
    print("--- INICIALIZANDO BASE DE DATOS Y COMPROBACIONES DE MANTENIMIENTO ---")
    inicializar_base_datos()
    
    # Crear datos simulados para probar la predicción de reabastecimiento
    print("\n[PROCESO] Creando datos simulados de ventas para Producto ID = 1...")
    insertar_datos_prueba_lstm(producto_id=1, existencia=8)
    
    # Importación dinámica del módulo de predicción
    print("\n[PROCESO] Cargando tubería LSTM y ejecutando predicción...")
    from prediccion_reabastecimiento import predecir_demanda_y_reabastecimiento
    
    # Consultar el estado del Producto ID = 1
    resultado = predecir_demanda_y_reabastecimiento(producto_id=1, lead_time_dias=3, stock_seguridad=5)
    
    print("\n--- INFORME DE REABASTECIMIENTO ---")
    print(f"Estado del Sistema: {resultado['estado']}")
    print(f"Stock Actual en BD: {resultado['stock_actual']}")
    
    if resultado['estado'] == 'MODO_DEEP_LEARNING':
        print(f"Demanda Estimada (Próx. 7 días): {resultado['demanda_proyectada_7dias']} unidades")
        print(f"Punto de Reorden (ROP): {resultado['punto_de_reorden']}")
    
    if resultado.get('alerta_compra') or resultado.get('alerta'):
        print(f"[ALERTA] Generar Orden de Compra por {resultado['cantidad_sugerida'] if resultado['estado'] == 'MODO_DEEP_LEARNING' else resultado['compra_sugerida']} unidades.")
    else:
        print("[OK] Stock suficiente.")