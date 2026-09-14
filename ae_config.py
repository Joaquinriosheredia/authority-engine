#!/usr/bin/env python3
"""
ae_config.py — Configuración compartida del pipeline Authority Engine.

Única fuente de verdad para rutas externas usadas por varios scripts del
pipeline (engine.py, openclaw_v9.py, generar_inventario.py). Antes de este
módulo, la ruta al repositorio de contenido externo (DAM-Java-Mastery)
estaba hardcodeada de forma independiente en tres sitios distintos.

cure.py NO importa este módulo directamente: sigue obteniendo la ruta
indirectamente a través de `from engine import CONFIG` (relación
preexistente, sin cambios).
"""

import os
from pathlib import Path

# Repositorio de contenido externo donde Authority Engine publica los
# documentos generados (DAM-Java-Mastery). Mismo valor por defecto que
# se usaba antes de esta configuración unificada.
DEFAULT_REPO_ROOT = Path.home() / ".openclaw" / "workspace" / "DAM-Java-Mastery"

# Histórico de auditorías SRE consumido por generar_inventario.py.
DEFAULT_AUDIT_LOG = Path.home() / ".openclaw" / "auditoria_sre_log.json"


def get_repo_root() -> Path:
    """Ruta al repositorio de contenido externo (DAM-Java-Mastery).

    Configurable con la variable de entorno AUTHORITY_ENGINE_REPO_ROOT.
    Si no está definida, usa DEFAULT_REPO_ROOT (mismo comportamiento que
    antes de esta configuración unificada).
    """
    valor = os.environ.get("AUTHORITY_ENGINE_REPO_ROOT")
    return Path(valor).expanduser() if valor else DEFAULT_REPO_ROOT


def get_audit_log_path() -> Path:
    """Ruta al histórico de auditorías SRE.

    Configurable con la variable de entorno AUTHORITY_ENGINE_AUDIT_LOG.
    Si no está definida, usa DEFAULT_AUDIT_LOG.
    """
    valor = os.environ.get("AUTHORITY_ENGINE_AUDIT_LOG")
    return Path(valor).expanduser() if valor else DEFAULT_AUDIT_LOG
