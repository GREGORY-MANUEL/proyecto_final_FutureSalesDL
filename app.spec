# -*- mode: python ; coding: utf-8 -*-
import os
from PyInstaller.utils.hooks import collect_all

# Include the Streamlit app plus the local core package
datas = [('app.py', '.')]
# Add the local package tree for `core` so imports like `from core.ia_engine import ...` work
for root, dirs, files in os.walk('core'):
    if '__pycache__' in dirs:
        dirs.remove('__pycache__')
    for filename in files:
        if filename.endswith(('.py', '.json')):
            src_path = os.path.join(root, filename)
            dst_dir = os.path.join('core', os.path.relpath(root, 'core'))
            datas.append((src_path, dst_dir))

binaries = []
hiddenimports = []

# Collect all dynamic components, templates, and libraries for streamlit, webview, and dependencies
for pkg in ['streamlit', 'webview', 'bcrypt', 'rapidfuzz', 'pdfplumber', 'openpyxl', 'xlsxwriter', 'requests', 'pandas', 'numpy', 'sklearn', 'torch', 'plotly']:
    tmp_ret = collect_all(pkg)
    datas += tmp_ret[0]
    binaries += tmp_ret[1]
    hiddenimports += tmp_ret[2]

# Streamlit loads app.py at runtime, so PyInstaller cannot discover these imports statically.
hiddenimports += ['generar_historial', 'core.prediccion_ventas']

# Deduplicate lists
datas = list(set(datas))
binaries = list(set(binaries))
hiddenimports = list(set(hiddenimports))

# Explicitly collect all DLLs from torch/lib to avoid missing c10.dll and dependencies
try:
    import torch as _torch
    _torch_pkg_dir = os.path.dirname(_torch.__file__)
except Exception:
    _torch_pkg_dir = None

if _torch_pkg_dir:
    _torch_lib_dir = os.path.join(_torch_pkg_dir, 'lib')
    if os.path.isdir(_torch_lib_dir):
        for _root, _dirs, _files in os.walk(_torch_lib_dir):
            for _filename in _files:
                if _filename.endswith(('.dll', '.so', '.pyd')):
                    _src_path = os.path.join(_root, _filename)
                    _rel_dir = os.path.relpath(_root, _torch_pkg_dir)
                    _dst_dir = os.path.join('torch', _rel_dir)
                    binaries.append((_src_path, _dst_dir))

from PyInstaller.utils.hooks import collect_dynamic_libs
import shutil

# 1. Asegurar que las librerías dinámicas de torch se incluyan (usando el hook que importaste)
binaries += collect_dynamic_libs('torch')

# 2. FORZAR la recolección de las dependencias de C++ y OpenMP (El verdadero causante del Error 1114)
dlls_criticas = ['vcruntime140_1.dll', 'msvcp140.dll', 'vcruntime140.dll', 'libiomp5md.dll']
for dll_name in dlls_criticas:
    dll_path = shutil.which(dll_name)
    if dll_path:
        # Colocamos estas DLLs en la raíz de _internal
        binaries.append((dll_path, '.'))

a = Analysis(
    ['launcher.py'],
    pathex=[os.path.abspath('.')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[os.path.join(os.path.abspath('.'), 'pyi-hooks')],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='GeneradorOC',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # Set console to False so no command window flashes when starting the app!
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='assets/icono_personal.png' if os.path.exists('assets/icono_personal.png') else None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GeneradorOC',
)
