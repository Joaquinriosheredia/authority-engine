"""Tests de engine.get_categoria() — documentan el orden REAL de evaluación
(if/elif en cascada: el primer bloque de keywords que matchea gana, no hay
scoring por número de coincidencias).
"""
import pytest

from engine import get_categoria


# Una keyword representativa por categoría es suficiente: dentro de un mismo
# bloque `any(kw in tema_lower for kw in [...])` todas las keywords tienen
# el mismo comportamiento (basta con probar el mecanismo `in`, no cada palabra).
@pytest.mark.parametrize(
    "tema, categoria_esperada",
    [
        ("Introducción a Kafka", "07_BigData_Streaming"),
        ("Desplegar en Kubernetes con Helm", "05_SRE_DevOps"),
        ("JWT y Zero Trust", "06_Seguridad"),
        ("RAG con LangChain4j", "08_IA_Agentes"),
        ("Componentes en React", "09_Frontend_Mobile"),
        ("Arquitectura Hexagonal y DDD", "02_Arquitectura"),
        ("Spring Boot con R2DBC", "03_Spring_Ecosystem"),
        ("Índices en PostgreSQL", "04_Bases_de_Datos"),
        ("Virtual Threads en Java 21", "01_Java_Core"),
    ],
)
def test_categoria_por_keyword_representativa(tema, categoria_esperada):
    assert get_categoria(tema) == categoria_esperada


def test_tema_sin_coincidencia_devuelve_vanguardia():
    assert get_categoria("Un tema totalmente inventado sin keywords") == "10_Vanguardia"


def test_case_insensitive():
    assert get_categoria("KAFKA Y STREAMING") == "07_BigData_Streaming"
    assert get_categoria("kafka y streaming") == "07_BigData_Streaming"


def test_colision_kafka_seguridad_gana_bigdata_por_orden_real():
    """REGLA DE NEGOCIO PROTEGIDA (no es un bug pendiente): get_categoria()
    clasifica en cascada y gana la primera categoría con keyword coincidente.
    07_BigData_Streaming se evalúa ANTES que 06_Seguridad, así que un tema que
    contiene tanto "kafka" como "seguridad" devuelve 07_BigData_Streaming,
    no 06_Seguridad, aunque ambos matcheen. Este orden es intencional; solo
    debe cambiarse como decisión de política de clasificación, no como
    refactor, y en ese caso este test debe actualizarse a propósito.
    """
    assert get_categoria("Seguridad en Kafka para microservicios") == "07_BigData_Streaming"
