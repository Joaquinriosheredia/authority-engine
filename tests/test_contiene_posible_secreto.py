"""Tests de generar_inventario.contiene_posible_secreto().

IMPORTANTE: todos los valores usados aquí son sintéticos/de ejemplo,
NUNCA credenciales reales (ver incidente histórico de la key de DeepL
expuesta en INVENTARIO_SISTEMA.md — no se repite ese patrón aquí).
La key AWS de ejemplo usada es el placeholder público oficial de AWS
(AKIAIOSFODNN7EXAMPLE), documentado como ejemplo no funcional en la
documentación de Amazon.
"""
import pytest

from generar_inventario import contiene_posible_secreto


@pytest.mark.parametrize(
    "texto",
    [
        'API_KEY = "sk-fake-0000000000000000"',
        "api_key='fake-token-value-aaaa'",
        'SECRET = "fake-secret-value"',
        'TOKEN = "fake-token-value"',
        'PASSWORD = "hunter2-not-real"',
        "AKIAIOSFODNN7EXAMPLE",  # placeholder público oficial de AWS
    ],
    ids=["api_key_mayus", "api_key_minus_guion_bajo", "secret", "token", "password", "aws_akia"],
)
def test_patrones_positivos_detectados(texto):
    assert contiene_posible_secreto(texto) is True


def test_texto_limpio_no_detecta_nada():
    texto = "def suma(a, b):\n    return a + b\n"
    assert contiene_posible_secreto(texto) is False


def test_valor_sin_comillas_no_se_detecta():
    """Comportamiento REAL actual: el regex exige comillas alrededor del
    valor (["'][^"']+["']). Un API_KEY=valor sin comillas NO se detecta.
    Este test documenta la limitación, no la corrige.
    """
    texto = "API_KEY=valor_sin_comillas_1234"
    assert contiene_posible_secreto(texto) is False


def test_valor_de_api_aislado_sin_prefijo_no_se_detecta():
    """Comportamiento REAL actual (limitación conocida, relevante para el
    incidente DeepL): un valor con forma de API key pero SIN ir precedido
    de API_KEY=/SECRET=/TOKEN=/PASSWORD= (p. ej. pegado suelto en un
    Markdown, como ocurrió con la key de DeepL) NO se detecta, porque
    ninguno de los 5 patrones busca el valor de forma aislada.
    Este test documenta la limitación actual, no la corrige.
    """
    texto = "La clave usada fue: fake0123456789fake0123456789fake012:fx"
    assert contiene_posible_secreto(texto) is False
