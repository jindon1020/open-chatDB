# -*- mode: python ; coding: utf-8 -*-
import sys
import platform

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('templates', 'templates'),
        ('static', 'static'),
    ],
    hiddenimports=[
        # uvicorn internals
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.loops.asyncio',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.http.httptools_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',
        'uvicorn.lifespan.off',
        # asgiref
        'asgiref',
        'asgiref.wsgi',
        # database drivers
        'pymysql',
        'pymongo',
        'elasticsearch',
        'sshtunnel',
        # project modules
        'config',
        'app',
        'run',
        'services',
        'services.connection_manager',
        'services.settings_manager',
        'services.llm_service',
        'services.mysql_service',
        'services.mongo_service',
        'services.elasticsearch_service',
        'services.schema_indexer',
        'routes',
        'routes.api_connections',
        'routes.api_database',
        'routes.api_query',
        'routes.api_schema',
        'routes.api_chat',
        'routes.api_settings',
        # stdlib / misc
        'dotenv',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='OpenChatDB',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False if sys.platform == 'darwin' else True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='OpenChatDB.app',
        icon=None,
        bundle_identifier='com.openchatdb.app',
    )
