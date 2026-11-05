# Manual de Instalación y Ejecución

Este documento explica cómo configurar y ejecutar el **Generador de Órdenes de Compra** en diferentes entornos.

## 1. Requisitos Previos

### Para Desarrollo (Python)
- **Python 3.11 o superior** instalado.
- Entorno virtual configurado (ya existe en la carpeta `.venv`).

### Para Empaquetado (Escritorio)
- **Node.js v20.x o superior** instalado.
- El proyecto utiliza `@stlite/desktop` para funcionar sin Python local.

---

## 2. Ejecución Local (Modo Desarrollo)

Si deseas realizar cambios y probarlos inmediatamente:

1. Abre una terminal en la carpeta del proyecto.
2. Asegúrate de que el entorno virtual esté activo (opcional si usas el script `.bat`):
   ```powershell
   .\.venv\Scripts\activate
   ```
3. Ejecuta la aplicación:
   ```powershell
   streamlit run app.py
   ```
4. También puedes usar el archivo **`Iniciar_App.bat`** incluido en la carpeta raíz para abrirlo con un doble clic.

---

## 3. Ejecución como App de Escritorio (Stlite)

Esta opción permite ejecutar la aplicación usando un navegador interno, sin necesidad de tener Python instalado en el equipo final.

### Generar o Actualizar el Paquete
Si has realizado cambios en el código (`app.py`) o en los archivos de la carpeta `archivos/`, debes regenerar el paquete:

```bash
npm run dump
```
Esto actualizará los archivos en la carpeta `build/`.

### Servir la Aplicación
Para abrir la aplicación empaquetada y verificar su funcionamiento:

```bash
npm run serve
```
La aplicación se abrirá en tu navegador predeterminado (o en una ventana dedicada si se configura un lanzador).

---

## 4. Estructura de Archivos Importante

- **`app.py`**: El código principal de la aplicación.
- **`archivos/`**: Carpeta donde se guardan los archivos PDF de inventario y catálogos que la aplicación necesita procesar.
- **`build/`**: Contiene la aplicación empaquetada para ser distribuida.
- **`package.json`**: Configuración de dependencias de Node.js y Stlite.
- **`requirements.txt`**: Lista de librerías de Python necesarias.

---

## 5. Notas sobre Dependencias

- **NUEVO**: Se ha reemplazado `pdfplumber` por `pypdf`. Si instalas la aplicación en un nuevo entorno virtual manualmente, usa:
  ```bash
  pip install streamlit pypdf pandas openpyxl xlsxwriter numpy
  ```
- No es necesario instalar `rapidfuzz` ni `fpdf`, ya que el código actual no las requiere.
