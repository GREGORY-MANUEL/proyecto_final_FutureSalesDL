import pandas as pd

# Leer el archivo original
df = pd.read_csv('datos_originales.txt', dtype={'FDI_CODIGO': str})

# Limpiar las comillas de la columna de código
df['FDI_CODIGO'] = df['FDI_CODIGO'].str.replace('"', '')

# Asignar la fecha y convertir las cantidades a enteros bajo la columna Ventas
df['Fecha'] = df['FDI_FECHAOPERACION']
df['Ventas'] = df['FDI_CANTIDAD'].fillna(0).astype(int)

# Extraer el día de la semana de la fecha (Lunes = 0, Domingo = 6)
df['Dia_Semana'] = pd.to_datetime(df['Fecha']).dt.weekday

# Determinar si hubo stock (1 si Ventas > 0, de lo contrario 0)
df['Hubo_Stock'] = (df['Ventas'] > 0).astype(int)

# Asignar 0 por defecto a Promocion_Activa
df['Promocion_Activa'] = 0

# Seleccionar y ordenar las columnas finales (se omite FDI_CANTIDAD y FDI_FECHAOPERACION)
columnas_finales = [
    'FDI_CODIGO', 'Fecha', 'Ventas', 'Dia_Semana', 'Promocion_Activa', 'Hubo_Stock'
]
df_final = df[columnas_finales]

# Exportar el resultado a un nuevo archivo CSV
df_final.to_csv('datos_formateados.csv', index=False)