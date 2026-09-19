# ADR-003: Aislamiento por grupo de procesos y timeouts en la cadena de ejecución

- **Estado:** Aceptada
- **Commits de referencia:** `ae5a905` (2026-09-17, `fix: kill full process group on ejecutar_tema timeout`) y `4eb6bee` (2026-09-17, `fix: add timeout to git subprocess calls in publish paths`). Relacionado: `d1411d5` (2026-09-17, lock del pipeline). Tickets B.4 / B.5.

## Context

La cadena es `openclaw_v9.py` → `racha.py` → `engine.py`. `openclaw_v9.ejecutar_tema()` usaba `subprocess.run(cmd, timeout=timeout)`. Ese timeout mata solo el hijo directo (`racha.py`): el `engine.py` que este había lanzado seguía ejecutándose huérfano pasado el plazo.

Además, las llamadas a `git` (`pull`, `add`, `commit`, `push`) en `engine.py`, `cure.py` y `generar_inventario.py` no tenían timeout, así que un `git` colgado (red, prompt de credenciales) podía bloquear el pipeline indefinidamente.

## Decision

- `openclaw_v9.py` lanza `racha.py` con `subprocess.Popen(cmd, start_new_session=True)` y `proceso.wait(timeout=timeout)`. Al vencer, mata todo el grupo con `os.killpg(os.getpgid(pid), SIGKILL)`, hace `proceso.wait()` para evitar zombies y captura `ProcessLookupError` si el grupo ya no existe.
- Como `racha.py` y `engine.py` no crean sesión propia, heredan el grupo y mueren juntos. `racha.py` no se modificó en este fix.
- Las llamadas `git` en las rutas de publicación llevan `timeout` (30 s; 10 s para `rebase --abort`; 60 s para `push`) y un `except subprocess.TimeoutExpired` que aborta la publicación con un log.
- Relacionado (`d1411d5`): `engine.acquire_lock()` solo borra el lock si `os.kill(pid, 0)` lanza `ProcessLookupError`; ante cualquier otro error asume que hay un proceso vivo y no arranca.

## Alternatives Considered

- **Mantener `subprocess.run(..., timeout=...)`**: insuficiente; no alcanza a los nietos. Es el comportamiento que se reemplazó.
- Los commits no documentan otras alternativas.

## Consequences

- Al vencer el timeout no quedan `racha.py` ni `engine.py` huérfanos, incluidos los `git` que estuvieran en curso.
- `SIGKILL` no permite limpieza: un `engine.py` matado no ejecuta sus manejadores `atexit` (p. ej. el borrado del lock), y el siguiente arranque depende de la lógica de `d1411d5`.
- Solo `openclaw_v9.py` es el punto de entrada protegido; ejecutar `racha.py` o `engine.py` directamente no aplica este aislamiento.
- Una publicación git que agota el tiempo se aborta y se registra, sin bloquear el resto.
