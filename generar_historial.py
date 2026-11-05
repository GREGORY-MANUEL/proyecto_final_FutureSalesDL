import numpy as np
import pandas as pd
from pathlib import Path


def generar_promociones_por_bloques(
    fechas_unicas, proporcion=0.20, duracion_min=3, duracion_max=7, seed=42
):
    """Genera promociones activas (0/1) por bloques de fechas consecutivas."""
    np.random.seed(seed)
    promociones = np.zeros(len(fechas_unicas), dtype=int)
    indice = 0

    while indice < len(fechas_unicas):
        if np.random.rand() < proporcion:
            duracion = np.random.randint(duracion_min, duracion_max + 1)
            promociones[indice : min(indice + duracion, len(fechas_unicas))] = 1
            indice += duracion
        else:
            indice += 1

    return pd.Series(promociones, index=fechas_unicas, name="Promocion_Activa")


def cargar_ventas_originales(archivo_txt, frecuencia="D"):
    """Convierte las columnas FDI del TXT a registros temporales por producto."""
    if frecuencia not in {"D", "W", "MS"}:
        raise ValueError("La frecuencia debe ser 'D' (diaria), 'W' (semanal) o 'MS' (mensual).")

    if hasattr(archivo_txt, "seek"):
        archivo_txt.seek(0)

    try:
        df = pd.read_csv(archivo_txt, sep=None, engine="python", dtype=str)
    except Exception as error:
        raise ValueError(f"No se pudo leer el TXT delimitado: {error}") from error

    df.columns = [str(col).replace("\ufeff", "").strip().upper() for col in df.columns]
    columnas_requeridas = {"FDI_CODIGO", "FDI_CANTIDAD", "FDI_FECHAOPERACION"}
    faltantes = columnas_requeridas.difference(df.columns)
    if faltantes:
        raise ValueError(
            "El archivo debe incluir las columnas FDI_CODIGO, FDI_CANTIDAD "
            "y FDI_FECHAOPERACION. Faltan: " + ", ".join(sorted(faltantes))
        )

    df = df.rename(
        columns={
            "FDI_CODIGO": "Producto_ID",
            "FDI_CANTIDAD": "Ventas",
            "FDI_FECHAOPERACION": "Fecha",
        }
    )
    df["Producto_ID"] = df["Producto_ID"].astype("string").str.strip()
    df["Fecha"] = pd.to_datetime(df["Fecha"], errors="coerce").dt.normalize()
    df["Ventas"] = pd.to_numeric(df["Ventas"], errors="coerce")
    
    # Eliminar el filtro estricto de años 2023-2026 para permitir 2021, 2022, etc.
    df = df.dropna(subset=["Producto_ID", "Fecha", "Ventas"])
    df = df[df["Producto_ID"].ne("")]
    if df.empty:
        raise ValueError("No se encontraron registros válidos en el archivo.")

    promo_col = next(
        (col for col in df.columns if "PROMOC" in col or "PROMO" in col), None
    )
    stock_col = next(
        (
            col
            for col in df.columns
            if col in {"HUBO_STOCK", "INVENTARIO", "INVENTARIO_FINAL", "EXISTENCIA"}
        ),
        None,
    )
    if promo_col:
        promo_values = df[promo_col].astype("string").str.strip().str.lower()
        promo_values = promo_values.replace(
            {"sí": "1", "si": "1", "true": "1", "yes": "1", "no": "0", "false": "0"}
        )
        df["Promocion_Activa"] = pd.to_numeric(promo_values, errors="coerce").fillna(0).clip(0, 1)
    else:
        fechas_unicas = pd.Series(df["Fecha"].unique()).sort_values().reset_index(drop=True)
        promociones = generar_promociones_por_bloques(fechas_unicas)
        mapa_promociones = dict(zip(fechas_unicas, promociones))
        df["Promocion_Activa"] = df["Fecha"].map(mapa_promociones).fillna(0).astype(int)

        np.random.seed(42)
        multiplicador_promo = np.random.uniform(1.8, 2.5, size=len(df))
        df["Ventas"] = np.where(
            df["Promocion_Activa"] == 1,
            df["Ventas"] * multiplicador_promo,
            df["Ventas"],
        )
    if stock_col:
        df["Hubo_Stock"] = (pd.to_numeric(df[stock_col], errors="coerce").fillna(0) > 0).astype(int)
    else:
        df["Hubo_Stock"] = 1

    # Adaptar fecha a la frecuencia deseada
    if frecuencia == 'W':
        df['Fecha'] = df['Fecha'] - pd.to_timedelta(df['Fecha'].dt.dayofweek, unit='d')
    elif frecuencia == 'MS':
        df['Fecha'] = df['Fecha'] - pd.to_timedelta(df['Fecha'].dt.day - 1, unit='d')

    # Agrupar por Producto y Fecha sumando ventas y tomando el max de las flags.
    # No utilizamos resample para evitar rellenar con ceros los días sin venta.
    diario = df.groupby(["Producto_ID", "Fecha"]).agg(
        {
            "Ventas": "sum",
            "Promocion_Activa": "max",
            "Hubo_Stock": "max",
        }
    ).reset_index()

    diario["Ventas"] = diario["Ventas"].round(2)
    diario["Dia_Semana"] = diario["Fecha"].dt.dayofweek
    diario = diario.sort_values(["Producto_ID", "Fecha"]).reset_index(drop=True)
    diario["Fecha"] = diario["Fecha"].dt.strftime("%Y-%m-%d")

    columnas = [
        "Producto_ID",
        "Fecha",
        "Ventas",
        "Dia_Semana",
        "Promocion_Activa",
        "Hubo_Stock",
    ]
    return diario[columnas]


def filtrar_dataset_entrenamiento(
    dataset, fecha_inicio="2023-01-01", fecha_fin="2026-12-31"
):
    """Filtra el dataset por fechas y devuelve las filas en orden cronológico."""
    resultado = dataset.copy()
    fechas = pd.to_datetime(resultado["Fecha"], errors="coerce")
    if fecha_inicio is not None:
        resultado = resultado.loc[fechas >= pd.Timestamp(fecha_inicio)].copy()
        fechas = fechas.loc[resultado.index]
    if fecha_fin is not None:
        resultado = resultado.loc[fechas <= pd.Timestamp(fecha_fin)].copy()
    if resultado.empty:
        raise ValueError("No hay ventas dentro del rango de fechas seleccionado.")
    resultado["Fecha"] = pd.to_datetime(resultado["Fecha"]).dt.strftime("%Y-%m-%d")
    return resultado.sort_values(["Producto_ID", "Fecha"]).reset_index(drop=True)


def generar_dataset_entrenamiento(
    archivo_txt,
    fecha_inicio="2023-01-01",
    fecha_fin="2026-12-31",
    frecuencia="D",
):
    """Lee el TXT original y genera el dataset de entrenamiento filtrado."""
    dataset = cargar_ventas_originales(archivo_txt, frecuencia=frecuencia)
    return filtrar_dataset_entrenamiento(dataset, fecha_inicio, fecha_fin)


def guardar_dataset_entrenamiento(datos_csv, directorio_base, fecha_guardado=None):
    """Guarda el CSV dentro de una carpeta nombrada con la fecha de guardado."""
    fecha_carpeta = pd.Timestamp(fecha_guardado or pd.Timestamp.now()).strftime("%Y-%m-%d")
    carpeta_destino = Path(directorio_base) / fecha_carpeta
    carpeta_destino.mkdir(parents=True, exist_ok=True)
    ruta_archivo = carpeta_destino / "dataset_entrenamiento.csv"
    ruta_archivo.write_bytes(datos_csv)
    return ruta_archivo