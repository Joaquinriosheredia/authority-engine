# ADR-001: Publicación definitiva con revisión humana en `cure.py`

- **Estado:** Aceptada
- **Commit de referencia:** `1448516` (2026-09-14, `feat: version pipeline orchestration scripts`) — versiona `cure.py` con este flujo. Decisión previa al resto de ADRs; no hay un commit posterior dedicado a ella.

## Context

`engine.py` genera un documento por secciones con un LLM y lo puntúa con `evaluar()` (heurísticas: longitud, bloque Java, Mermaid, setters, `record ... extends`). Ese score es una comprobación mecánica, no un juicio sobre la calidad técnica del contenido.

El pipeline separa dos destinos en el repo de contenido:

- `_Review/`: borradores. `engine.py` los sube solo (`git_push_review`, mensaje `draft: ... — pendiente revisión Claude`).
- `<categoría>/`: publicación definitiva.

## Decision

La publicación definitiva **no es automática**. Solo ocurre desde `cure.py`, con este flujo:

1. Una persona pega en stdin el documento refinado (`cure.py` lo recibe por `stdin`).
2. `cure.py` hace backup, recalcula el score y rechaza si `score <= 50`.
3. Muestra el diff y pide confirmación explícita (`¿Aplicar cambios? [s/N]`; por defecto, no).
4. Solo si se confirma **y** `score >= SCORE_DEPLOY` (72), mueve el archivo a su categoría y hace `git_push_definitivo`. Si el score es menor, se queda en `_Review/`.

## Alternatives Considered

- **Publicación automática end-to-end** (engine → categoría final sin intervención): descartada por diseño; el código no la implementa. Los commits no recogen una motivación explícita más allá de la propia existencia del flujo Review (borrador → refinado → confirmación).

## Consequences

- Nada llega a las carpetas de categoría sin un `s` humano sobre un diff visible.
- El pipeline nunca es totalmente desatendido: `engine.py` produce borradores automáticamente, pero la salida final requiere una sesión interactiva de `cure.py`.
- El auto-push a `_Review/` sigue siendo automático; por eso ADR-002 controla cuándo un borrador puede subirse solo.
- Coste: el throughput queda limitado por la revisión manual.
