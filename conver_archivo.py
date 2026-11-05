import pandas as pd
import os

# 1. Definir las rutas exactas (cambia el nombre del .txt si es diferente)
ruta_entrada = r'C:\GC - PURCHASING TECH\archivos\sales-prediction-with-deep-learning-main\data2\datos_originales.txt'
ruta_salida = r'C:\GC - PURCHASING TECH\archivos\sales-prediction-with-deep-learning-main\data2\datos_convertidos.csv'

# 2. Asegurar que la carpeta de destino exista
carpeta_destino = os.path.dirname(ruta_salida)
if not os.path.exists(carpeta_destino):
    os.makedirs(carpeta_destino) # Crea las carpetas si no existen

try:
    # 3. Leer el archivo
    df = pd.read_csv(ruta_entrada, dtype={'FDI_CODIGO': str})

    # 4. Renombrar columnas
    df = df.rename(columns={
        'FDI_CODIGO': 'id',
        'FDI_CANTIDAD': 'sale',
        'FDI_FECHAOPERACION': 'date'
    })

    # 5. Agregar la tienda
    df['store'] = '1'

    # 6. Exportar
    df.to_csv(ruta_salida, index=False)
    print("¡El archivo ha sido convertido exitosamente!")

except FileNotFoundError:
    print(f"❌ ERROR: No se encontró el archivo original en la ruta:\n{ruta_entrada}\nVerifica que el archivo esté allí y se llame exactamente así.")
except PermissionError:
    print("❌ ERROR: Permiso denegado. Si tienes el archivo CSV abierto en Excel u otro programa, ciérralo e intenta de nuevo.")
except Exception as e:
    print(f"❌ ERROR INESPERADO: {e}")