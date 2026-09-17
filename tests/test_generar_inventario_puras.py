"""Tests de las funciones puras de generar_inventario.py: fmt_size() y
sre_stats_por_carpeta()."""
import pytest

from generar_inventario import fmt_size, sre_stats_por_carpeta


@pytest.mark.parametrize(
    "size_bytes, esperado",
    [
        (0, "0.0B"),
        (1023, "1023.0B"),
        (1024, "1.0KB"),
        (1024 * 1024, "1.0MB"),
        (1024 * 1024 * 1024, "1.0GB"),
        (1024 * 1024 * 1024 * 1024, "1.0TB"),
    ],
)
def test_fmt_size(size_bytes, esperado):
    assert fmt_size(size_bytes) == esperado


class TestSreStatsPorCarpeta:
    def test_historico_vacio(self):
        assert sre_stats_por_carpeta([]) == {}

    def test_una_entrada(self):
        historico = [{"archivo": "02_Arquitectura/doc_STAFF.md", "score": 80}]
        resultado = sre_stats_por_carpeta(historico)
        assert resultado == {
            "02_Arquitectura": {"total": 1, "promedio": 80.0, "maximo": 80, "minimo": 80}
        }

    def test_varias_entradas_misma_carpeta(self):
        historico = [
            {"archivo": "02_Arquitectura/a_STAFF.md", "score": 80},
            {"archivo": "02_Arquitectura/b_STAFF.md", "score": 90},
            {"archivo": "02_Arquitectura/c_STAFF.md", "score": 70},
        ]
        resultado = sre_stats_por_carpeta(historico)
        assert resultado["02_Arquitectura"] == {
            "total": 3, "promedio": 80.0, "maximo": 90, "minimo": 70
        }

    def test_carpeta_desconocida_se_ignora(self):
        """Solo se agregan carpetas presentes en CARPETAS_REPO; cualquier
        otra ruta se descarta silenciosamente."""
        historico = [{"archivo": "una_carpeta_inventada/doc.md", "score": 50}]
        assert sre_stats_por_carpeta(historico) == {}

    def test_claves_faltantes_usan_defaults(self):
        """entry sin "archivo" ni "score" no rompe la función (usa .get
        con defaults "" y 0), y al no matchear ninguna CARPETAS_REPO
        tampoco contribuye a ninguna carpeta."""
        historico = [{}]
        assert sre_stats_por_carpeta(historico) == {}
