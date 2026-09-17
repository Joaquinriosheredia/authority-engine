"""Tests de engine.obtener_secciones_maestras().

IMPORTANTE (hallazgo de la auditoría, confirmado empíricamente aquí):
los comentarios del propio código dicen "5/7/9/12 secciones" por bucket,
pero esos totales SOLO se cumplen si además hay match de una keyword
contextual (seguridad/testing/rendimiento). Sin esa coincidencia extra,
los totales reales son 5/6/8/11 (simple/medio/complejo/completo) y el
default es 6, no 7. Estos tests documentan el comportamiento REAL, no
el que sugiere el comentario del código.
"""
from engine import obtener_secciones_maestras


def test_bucket_simple_sin_contextual_da_5_secciones():
    secciones = obtener_secciones_maestras("Observer Pattern")
    assert len(secciones) == 5
    assert secciones[-1] == "Conclusiones"


def test_bucket_medio_sin_contextual_da_6_no_7():
    """El comentario del código dice "7 secciones" para este bucket, pero
    sin keyword contextual el total real es 6 (4 base + 2 del bucket)."""
    secciones = obtener_secciones_maestras("Spring Boot con R2DBC")
    assert len(secciones) == 6
    assert "Patrones de Integración" in secciones


def test_bucket_complejo_sin_contextual_da_8_no_9():
    """El comentario del código dice "9 secciones"; real: 8 sin contextual."""
    secciones = obtener_secciones_maestras("CQRS y Saga")
    assert len(secciones) == 8
    assert "Escalabilidad y Alta Disponibilidad" in secciones


def test_bucket_completo_sin_contextual_da_11_no_12():
    """El comentario del código dice "12 secciones"; real: 11 sin contextual."""
    secciones = obtener_secciones_maestras("Ecosistema de plataforma")
    assert len(secciones) == 11
    assert "Migración y Compatibilidad" in secciones


def test_default_sin_contextual_da_6():
    secciones = obtener_secciones_maestras("Un tema random cualquiera")
    assert len(secciones) == 6
    assert secciones[-2:] == ["Patrones de Integración", "Conclusiones"]


def test_colision_factory_kafka_gana_bucket_simple():
    """'factory' (bucket simple) se comprueba antes que 'kafka' (bucket
    complejo) y el bucket simple hace return inmediato: gana simple."""
    secciones = obtener_secciones_maestras("Factory pattern con Kafka")
    assert len(secciones) == 5


def test_prioridad_contextual_seguridad_sobre_testing():
    """Cuando un tema matchea keywords de seguridad Y de testing a la vez,
    gana seguridad porque es el primer `if` en la cascada."""
    secciones = obtener_secciones_maestras("JWT y Testing con Mockito")
    assert "Seguridad y Superficie de Ataque" in secciones
    assert "Validación y Estrategia de Pruebas" not in secciones


def test_prioridad_contextual_testing_sobre_rendimiento():
    """Testing se comprueba antes que rendimiento en la cascada."""
    secciones = obtener_secciones_maestras("Testing de Rendimiento con Benchmark")
    assert "Validación y Estrategia de Pruebas" in secciones
    assert "Rendimiento y Capacidad Crítica" not in secciones
