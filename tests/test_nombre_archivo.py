"""Tests de las 3 implementaciones de nombre_archivo():
- engine.nombre_archivo            -> sufijo ".md"
- openclaw_v9.nombre_archivo       -> sufijo ".md" (duplicado literal de engine.py)
- cure.nombre_archivo              -> sufijo "_STAFF.md"

No se fuerza que las tres sean idénticas: cure.py usa un sufijo distinto
a propósito (documentos ya revisados por Claude). Sí se documenta que
engine.py y openclaw_v9.py son duplicados exactos.
"""
import pytest

from engine import nombre_archivo as nombre_archivo_engine
from openclaw_v9 import nombre_archivo as nombre_archivo_openclaw
from cure import nombre_archivo as nombre_archivo_cure


@pytest.mark.parametrize(
    "nombre_archivo_fn, sufijo",
    [
        (nombre_archivo_engine, ".md"),
        (nombre_archivo_openclaw, ".md"),
        (nombre_archivo_cure, "_STAFF.md"),
    ],
    ids=["engine", "openclaw_v9", "cure"],
)
class TestNombreArchivoComun:
    def test_tema_normal(self, nombre_archivo_fn, sufijo):
        assert nombre_archivo_fn("Kafka Streams") == "kafka_streams" + sufijo

    def test_tema_con_acentos_se_conservan(self, nombre_archivo_fn, sufijo):
        # \w en Python 3 (modo unicode por defecto) incluye letras acentuadas,
        # así que NO se transliteran ni se eliminan.
        assert nombre_archivo_fn("Optimización JVM") == "optimización_jvm" + sufijo

    def test_emojis_y_puntuacion_se_eliminan(self, nombre_archivo_fn, sufijo):
        assert nombre_archivo_fn("Kafka!! 🔥 (avanzado)") == "kafka_avanzado" + sufijo

    def test_mas_de_80_caracteres_se_trunca_antes_del_sufijo(self, nombre_archivo_fn, sufijo):
        tema = "palabra " * 20  # bastante más de 80 caracteres tras la limpieza
        resultado = nombre_archivo_fn(tema)
        cuerpo = resultado[: -len(sufijo)]
        assert len(cuerpo) == 80
        assert resultado == cuerpo + sufijo

    def test_tema_vacio(self, nombre_archivo_fn, sufijo):
        assert nombre_archivo_fn("") == sufijo


def test_engine_y_openclaw_producen_el_mismo_resultado():
    """Documenta que engine.py y openclaw_v9.py implementan la misma lógica
    de forma duplicada e independiente (código repetido, ver auditoría)."""
    temas = ["Kafka Streams", "Optimización JVM", "", "Tema con Ñ y 🔥 emojis!!!"]
    for tema in temas:
        assert nombre_archivo_engine(tema) == nombre_archivo_openclaw(tema)
