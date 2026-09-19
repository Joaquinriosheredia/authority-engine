"""Tests de engine.evaluar() — documentan el comportamiento REAL actual.

Umbrales reales usados por el código (engine.py):
- CONFIG["MIN_WORDS"] = 300
- deducciones: texto_corto -40, falta_bloque_java -30, falta_bloque_mermaid -30,
  mermaid_sin_cabecera_graph_TD_o_LR -30, setter_detectado -20,
  record_no_puede_usar_extends -40
- score final = max(score, 0)
"""
import pytest

from engine import CONFIG, evaluar

MIN_WORDS = CONFIG["MIN_WORDS"]


def texto_largo(n_palabras=MIN_WORDS):
    """Genera un texto de exactamente n_palabras palabras."""
    return " ".join(["palabra"] * n_palabras)


def texto_valido_100():
    """Texto que satisface las 4 condiciones positivas de evaluar():
    >= MIN_WORDS palabras, bloque java, bloque mermaid con graph TD,
    sin setters y sin `record ... extends`.
    """
    relleno = " ".join(["palabra"] * MIN_WORDS)
    return (
        f"{relleno}\n"
        "```java\n"
        "public record Punto(int x, int y) {}\n"
        "```\n"
        "```mermaid\n"
        "graph TD\n"
        "  A --> B\n"
        "```\n"
    )


class TestEvaluarCasosBase:
    def test_texto_vacio_devuelve_cero_y_error(self):
        score, errores = evaluar("")
        assert score == 0
        assert errores == ["error"]

    def test_texto_none_devuelve_cero_y_error(self):
        # evaluar() comprueba "if not texto" -> None también cae en esta rama
        score, errores = evaluar(None)
        assert score == 0
        assert errores == ["error"]

    def test_error_ia_devuelve_cero_y_error(self):
        score, errores = evaluar("ERROR_IA")
        assert score == 0
        assert errores == ["error"]

    def test_texto_corto_penaliza_40(self):
        # < 300 palabras pero con bloque java y mermaid(TD) válidos,
        # así que la ÚNICA deducción aplicable es texto_corto.
        texto = "```java\ncode\n```\n```mermaid\ngraph TD\n```"
        score, errores = evaluar(texto)
        assert errores == ["texto_corto"]
        assert score == 60

    def test_texto_sin_bloque_java(self):
        texto = texto_largo() + "\n```mermaid\ngraph TD\n```"
        score, errores = evaluar(texto)
        assert errores == ["falta_bloque_java"]
        assert score == 70

    def test_texto_sin_bloque_mermaid(self):
        texto = texto_largo() + "\n```java\ncode\n```"
        score, errores = evaluar(texto)
        assert errores == ["falta_bloque_mermaid"]
        assert score == 70

    def test_mermaid_presente_pero_sin_graph_td_lr(self):
        # Bloque mermaid presente, pero sin cabecera "graph TD" ni "graph LR"
        texto = texto_largo() + "\n```java\ncode\n```\n```mermaid\nA --> B\n```"
        score, errores = evaluar(texto)
        assert "mermaid_sin_cabecera_graph_TD_o_LR" in errores
        assert "falta_bloque_mermaid" not in errores  # el bloque SÍ está presente

    @pytest.mark.parametrize("direccion", ["TB", "BT"])
    def test_mermaid_graph_tb_bt_fallan_actualmente(self, direccion):
        """Comportamiento REAL actual: solo TD y LR pasan el criterio.

        graph TB / graph BT son direcciones válidas de Mermaid pero el
        regex de evaluar() (r'graph\\s+(TD|LR)') NO las reconoce, así que
        se penalizan igual que si faltara la cabecera por completo.
        Este test documenta esa limitación, no la corrige.
        """
        texto = texto_largo() + f"\n```java\ncode\n```\n```mermaid\ngraph {direccion}\nA --> B\n```"
        score, errores = evaluar(texto)
        assert "mermaid_sin_cabecera_graph_TD_o_LR" in errores

    @pytest.mark.parametrize("direccion", ["TD", "LR"])
    def test_mermaid_graph_td_lr_pasan(self, direccion):
        texto = texto_largo() + f"\n```java\ncode\n```\n```mermaid\ngraph {direccion}\nA --> B\n```"
        score, errores = evaluar(texto)
        assert "mermaid_sin_cabecera_graph_TD_o_LR" not in errores
        assert "falta_bloque_mermaid" not in errores

    def test_setter_detectado(self):
        texto = texto_valido_100() + "\nobj.setNombre(x);"
        score, errores = evaluar(texto)
        assert "setter_detectado" in errores

    def test_record_extends_misma_linea_detectado(self):
        texto = texto_largo() + "\n```java\npublic record Foo(int x) extends Bar {}\n```\n```mermaid\ngraph TD\n```"
        score, errores = evaluar(texto)
        assert "record_no_puede_usar_extends" in errores

    def test_record_extends_separado_por_salto_de_linea_detectado(self):
        """El regex acota el rango a la firma de la declaración
        (r'\\brecord\\b(?:[^{;`.]|\\.(?=\\w))*\\bextends\\b'): la clase negada
        cruza saltos de línea, así que "extends" en la línea siguiente
        dentro de la firma SÍ se detecta.
        """
        texto = (
            texto_largo()
            + "\n```java\npublic record Foo(int x)\n    extends Bar {}\n```"
            + "\n```mermaid\ngraph TD\n```"
        )
        score, errores = evaluar(texto)
        assert "record_no_puede_usar_extends" in errores

    def test_record_extends_con_identificador_con_punto_detectado(self):
        """Un punto seguido de \\w (java.util.List) no corta el rango."""
        texto = (
            texto_largo()
            + "\n```java\npublic record Foo(java.util.List<String> xs)\n    extends Bar {}\n```"
            + "\n```mermaid\ngraph TD\n```"
        )
        score, errores = evaluar(texto)
        assert "record_no_puede_usar_extends" in errores

    def test_record_en_prosa_y_extends_no_relacionado_no_detectado(self):
        """Falso positivo evitado: 'record' en prosa y una clase con extends
        más adelante, sin { ni ; entre medias, ya no dispara el error
        porque el punto + espacio/salto de línea corta el rango."""
        texto = (
            texto_largo()
            + "\nUsa un record aquí.\nLuego class A extends B"
            + "\n```java\nclass Foo {}\n```"
            + "\n```mermaid\ngraph TD\n```"
        )
        score, errores = evaluar(texto)
        assert "record_no_puede_usar_extends" not in errores

    def test_record_valido_y_clase_extends_posterior_no_detectado(self):
        texto = (
            texto_largo()
            + "\n```java\nrecord Foo(int x) {}\nclass A extends B {}\n```"
            + "\n```mermaid\ngraph TD\n```"
        )
        score, errores = evaluar(texto)
        assert "record_no_puede_usar_extends" not in errores

    def test_acumulacion_de_penalizaciones(self):
        """Un texto corto, sin java, sin mermaid acumula las 3 deducciones."""
        texto = "hola"
        score, errores = evaluar(texto)
        assert score == 100 - 40 - 30 - 30  # 0, pero via acumulación real
        assert set(errores) == {"texto_corto", "falta_bloque_java", "falta_bloque_mermaid"}

    def test_score_nunca_negativo(self):
        """Un texto corto con setter y record...extends supera -100 en teoría
        (-40 -30 -30 -30 -20 -40 = -190) pero el score se clampa a 0."""
        texto = "obj.setX(1); record Foo extends Bar {}"
        score, errores = evaluar(texto)
        assert score == 0

    def test_caso_valido_alcanza_100(self):
        score, errores = evaluar(texto_valido_100())
        assert score == 100
        assert errores == []
