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
        "tvly-" + "A" * 40,  # formato real: prefijo tvly- + 40 alfanuméricos
        "279a2e9d-83b3-c416-7e2d-f721593e42a0:fx",  # UUID + :fx (plan Free, formato oficial de DeepL)
        "279a2e9d-83b3-c416-7e2d-f721593e42a0:pro",  # UUID + :pro (defensivo, no confirmado oficialmente)
    ],
    ids=[
        "api_key_mayus",
        "api_key_minus_guion_bajo",
        "secret",
        "token",
        "password",
        "aws_akia",
        "tavily_tvly",
        "deepl_uuid_fx",
        "deepl_uuid_pro",
    ],
)
def test_patrones_positivos_detectados(texto):
    assert contiene_posible_secreto(texto) is True


def test_tavily_key_aislada_sin_prefijo_se_detecta():
    """Ticket 3: a diferencia de un secreto genérico, una key de Tavily con
    forma "tvly-" + 40 alfanuméricos SÍ se detecta aunque aparezca suelta
    en el texto, sin ir precedida de "API_KEY=" ni similar.
    """
    texto = "En el .env de pruebas dejamos: tvly-" + "b" * 40 + " por error."
    assert contiene_posible_secreto(texto) is True


def test_deepl_key_aislada_sin_prefijo_se_detecta():
    """Ticket 3: replica exactamente el escenario del incidente histórico
    (key de DeepL pegada suelta en un Markdown, sin "API_KEY=" delante).
    Con el nuevo patrón dedicado, SÍ se detecta.
    """
    texto = "La clave usada fue: 279a2e9d-83b3-c416-7e2d-f721593e42a0:fx"
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


def test_valor_generico_aislado_sin_prefijo_ni_forma_conocida_no_se_detecta():
    """Comportamiento REAL actual (limitación conocida, ya no aplica a
    Tavily/DeepL desde el Ticket 3, pero sí a cualquier otro servicio): un
    valor con forma de API key pero SIN ir precedido de
    API_KEY=/SECRET=/TOKEN=/PASSWORD= y SIN encajar en el formato dedicado
    de Tavily o DeepL (p. ej. una key de OpenAI o Anthropic pegada suelta)
    sigue sin detectarse. Este test documenta la limitación restante,
    no la corrige — sigue sin ser un scanner genérico.
    """
    texto = "La clave usada fue: sk-fake0123456789fake0123456789fake0123456789"
    assert contiene_posible_secreto(texto) is False
