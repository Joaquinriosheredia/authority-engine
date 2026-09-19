# ADR-005: La clasificación por cascada de primer acierto es política, no un bug

- **Estado:** Aceptada
- **Commit de referencia:** `e98143a` (2026-09-19, `docs: document category cascade as intentional classification policy, not a bug`) — ticket 2. Test de la colisión introducido en `e48e386`.

## Context

`get_categoria(tema)` en `engine.py` recorre las categorías en un orden fijo con `if/elif`, y devuelve la primera cuyo listado de keywords aparezca en el tema. El orden es: `07_BigData_Streaming`, `05_SRE_DevOps`, `06_Seguridad`, `08_IA_Agentes`, `09_Frontend_Mobile`, `02_Arquitectura`, `03_Spring_Ecosystem`, `04_Bases_de_Datos`, `01_Java_Core`; sin coincidencia, `10_Vanguardia`.

Un tema que encaja en varias categorías se asigna a la que se evalúa antes. Ejemplo cubierto por test: `"Seguridad en Kafka para microservicios"` → `07_BigData_Streaming`, no `06_Seguridad`.

Se diagnosticó como posible bug; la decisión fue cerrarlo sin cambiar la lógica.

## Decision

Se mantiene la cascada de primer acierto y se documenta como **política de clasificación intencional**:

- Comentario de contrato sobre `get_categoria()`: el orden es intencional y solo debe cambiarse como decisión de política de clasificación, no como refactor.
- El test `test_colision_kafka_seguridad_gana_bigdata_por_orden_real` queda descrito como regla de negocio protegida. Su aserción no cambió.
- La lógica de `get_categoria()` no se tocó.

## Alternatives Considered

- **Scoring por número de keywords coincidentes** (o cualquier reparto ponderado): no adoptado. Los commits no registran un análisis comparativo; se decidió no cambiar el comportamiento existente.
- **Reordenar la cascada**: no realizado; cualquier reordenación cambia la categoría de temas existentes y se reserva a una decisión de política.

## Consequences

- Determinismo: el mismo tema siempre cae en la misma carpeta, y el resultado se explica leyendo el orden del código.
- El orden de las ramas es parte del contrato: mover una rama puede reclasificar temas sin que ningún test de keyword aislada lo detecte (la colisión kafka/seguridad sí está protegida por test).
- Los temas multi-categoría quedan en la categoría de mayor prioridad, aunque otra encaje igual de bien.
- Cambiar esto exige una decisión explícita y actualizar el test a propósito.
