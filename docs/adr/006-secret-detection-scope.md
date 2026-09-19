# ADR-006: Alcance de la detección de secretos: allowlist explícita + patrones conocidos

- **Estado:** Aceptada
- **Commits de referencia:** `2866375` (2026-09-14, `feat: unify DAM-Java-Mastery config and harden inventory allowlist`) y `2f78be2` (2026-09-17, `feat: detect Tavily and DeepL API key formats in secret scanner`). Tests: `tests/test_contiene_posible_secreto.py`.

## Context

`generar_inventario.py` vuelca el contenido de scripts en `INVENTARIO_SISTEMA.md`. Existía un incidente conocido: una credencial literal (una key de DeepL) terminó expuesta en ese inventario. Además, el inventario descubría los scripts con `BASE_DIR.glob("*.py")`, de modo que cualquier `.py` nuevo de la raíz (incluida una herramienta de un cliente ajeno) se volcaba automáticamente.

## Decision

Dos controles, deliberadamente acotados:

1. **Allowlist explícita** `PIPELINE_SCRIPTS`: solo `engine.py`, `racha.py`, `cure.py`, `openclaw_v9.py` y `generar_inventario.py` se vuelcan. Un `.py` nuevo no se descubre; hay que añadirlo a mano. Los scripts de la lista que no existen se omiten con un aviso.
2. **Patrones conocidos** (`PATRONES_SECRETO`, `contiene_posible_secreto`), aplicados a cada script antes de volcarlo:
   - Asignaciones literales tipo `API_KEY`, `SECRET`, `TOKEN`, `PASSWORD` con valor entre comillas.
   - Claves de acceso AWS: `AKIA[0-9A-Z]{16}`.
   - Tavily: `tvly-` + 40 alfanuméricos (`2f78be2`).
   - DeepL: UUID con sufijo `:fx` o `:pro` (`2f78be2`). El sufijo `:fx` está confirmado en la documentación oficial (plan Free); `:pro` se incluye de forma defensiva.

   Si hay coincidencia, el contenido se sustituye por un aviso de "CONTENIDO OMITIDO" y se registra en consola.

El propio código declara: "No es un scanner genérico".

## Alternatives Considered

- **Scanner genérico de secretos** (alta entropía, reglas amplias): descartado; el comentario del código lo excluye expresamente. Los commits no documentan un análisis más extenso.
- **Descubrimiento automático con glob**: es el mecanismo previo y el que se reemplazó.

## Consequences

- Superficie mínima y predecible: solo cinco ficheros pueden entrar al inventario.
- Cobertura limitada a los servicios que usa/usó el pipeline (Tavily, DeepL, AWS) y a asignaciones literales; un secreto de otro proveedor, o un valor sin comillas o sin prefijo reconocible, **no** se detecta (los tests documentan ese límite).
- Cada script nuevo del pipeline exige una edición manual de `PIPELINE_SCRIPTS`, y cada servicio nuevo, un patrón nuevo con su test.
- Riesgo de falso positivo aceptado: se prefiere omitir contenido a exponer un secreto.
