# ADR-002: Una sección fallida bloquea el auto-publish

- **Estado:** Aceptada
- **Commit de referencia:** `58959fb` (2026-09-16, `fix: block auto-publish when a section fails generation (score 0 / ERROR_IA)`) — ticket B.2.

## Context

`generate_report()` en `engine.py` calcula el score total como media de los scores de sección. Antes del fix, solo entraban en la media las secciones con `score >= 50`:

```python
if score >= 50:
    scores.append(score)
```

Una sección con `ERROR_IA` / score 0 quedaba **fuera** de la media, así que el total no reflejaba el fallo y el documento podía subirse automáticamente a `_Review/` (`git_push_review`) y figurar como aprobado en `score_historico.json`.

## Decision

- Todos los scores entran en la media (`scores.append(score)` sin filtro).
- Se marca `tiene_seccion_fallida` si algún score es `0` o el contenido es `"ERROR_IA"`.
- Si hay sección fallida: el documento se escribe igualmente en `_Review/` con una línea `⚠️ ADVERTENCIA` al inicio, **no** se llama a `git_push_review`, y se registra en el log.
- En `score_historico.json` se guarda `tiene_seccion_fallida` y `aprobado` pasa a ser `total >= SCORE_DEPLOY and not tiene_seccion_fallida`.

## Alternatives Considered

- **Mantener el comportamiento anterior** (excluir secciones < 50 de la media): descartada; oculta el fallo.
- **Publicar con solo la advertencia**: el fix conserva la advertencia en el archivo, pero también bloquea el push. El commit no documenta otras alternativas.

## Consequences

- Un fallo de generación en una sola sección ya no puede quedar enmascarado por un buen promedio.
- Un documento con fallo sigue existiendo en local para su revisión, pero no llega al remoto sin acción humana.
- Los documentos bloqueados quedan sin publicar hasta que alguien los corrija (encaja con ADR-001).
- El score total baja cuando hay secciones en 0 (efecto secundario de incluirlas en la media).
