# ADR-004: Directorio base derivado de `__file__`, no de rutas hardcodeadas

- **Estado:** Aceptada
- **Commit de referencia:** `be6767a` (2026-09-16, `fix: derive pipeline base dir from module location, use sys.executable in racha.py`) — ticket B.7.

## Context

Cinco scripts (`engine.py`, `racha.py`, `openclaw_v9.py`, `generar_inventario.py`, `cure.py`) construían sus rutas con `Path.home() / "AuthorityEngine"` (o `~/AuthorityEngine/...` en mensajes). El pipeline solo funcionaba si el repo estaba clonado exactamente en ese directorio. `racha.py` además invocaba `"python3"` a mano en vez del intérprete en uso.

## Decision

- Se añade `get_base_dir()` en `ae_config.py`: `return Path(__file__).resolve().parent`.
- Los scripts sustituyen los hardcodes por `get_base_dir()` (`LOG_FILE`, `CACHE_FILE`, `score_historico.json`, `BASE_DIR`, rutas de `racha.py`).
- `racha.py` lanza `engine.py` con `sys.executable` en lugar de `"python3"`.
- Esta ruta **no** es configurable por variable de entorno, a diferencia de `get_repo_root()` y `get_audit_log_path()` (`AUTHORITY_ENGINE_REPO_ROOT`, `AUTHORITY_ENGINE_AUDIT_LOG`): el directorio del código es el del propio módulo.

## Alternatives Considered

- **Variable de entorno también para el directorio base**: no adoptada; el docstring de `get_base_dir()` fija explícitamente que se deriva de la ubicación real del módulo.
- **Mantener `~/AuthorityEngine` hardcodeado**: es el estado previo que se elimina.

## Consequences

- El pipeline funciona desde cualquier directorio de clonado; esto permitió extraer el repo como `authority-engine` (`~/AuthorityEngine-extract`).
- Los artefactos generados (`engine.log`, `section_cache.json`, `score_historico.json`, `racha.log`) viven junto al código.
- `ae_config.py` debe permanecer en el mismo directorio que los scripts; si se mueve, la base cambia con él.
- Los mensajes de ayuda ya no nombran una ruta fija.
