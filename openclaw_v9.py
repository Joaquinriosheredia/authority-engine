#!/usr/bin/env python3
"""
openclaw_v9.py v9.2 — Burst Operator
Authority Engine — Joaquín Ríos Heredia

Mejoras v9.2:
- argparse con --dry-run, --modo, --retry, --cooldown
- Timeout por tema (evita cuelgues infinitos)
- Reintento automático configurable por tema fallido
- ETA en tiempo real por tema
- Persistencia de resultados en JSON
- Resumen final enriquecido con tasa de éxito
"""

import os
import re
import sys
import time
import json
import argparse
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta

# ── CONFIGURACIÓN ──────────────────────────────────────────────────────────────
BASE_DIR     = Path.home() / "AuthorityEngine"
LISTA_TEMAS  = BASE_DIR / "temas_rafaga.txt"
LOG_FILE     = BASE_DIR / "openclaw.log"
RACHA_SCRIPT = BASE_DIR / "racha.py"
RESULTS_FILE = BASE_DIR / "openclaw_results.json"
REPO_ROOT    = Path.home() / ".openclaw/workspace/DAM-Java-Mastery"

# ── LOGGING ────────────────────────────────────────────────────────────────────
BASE_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("OpenClaw")


# ── UTILIDADES ─────────────────────────────────────────────────────────────────
def fmt_eta(segundos: float) -> str:
    """Formatea segundos en HH:MM:SS legible."""
    return str(timedelta(seconds=int(segundos)))


def guardar_resultados(resultados: dict):
    """Persiste el resumen de la ráfaga en JSON para auditoría posterior."""
    resultados["timestamp"] = datetime.now().isoformat()
    with open(RESULTS_FILE, "w", encoding="utf-8") as f:
        json.dump(resultados, f, indent=2, ensure_ascii=False)
    log.info(f"📁 Resultados guardados en: {RESULTS_FILE}")


def inicializar_lista() -> bool:
    """Crea archivo de temas de ejemplo si no existe. Retorna False si fue creado."""
    if not LISTA_TEMAS.exists():
        ejemplos = [
            "Patrones de Resiliencia (Circuit Breaker y Retry) en Microservicios",
            "Estrategias de Migración de Monolito a Arquitectura Hexagonal",
            "Implementación de Zero Trust Security en APIs RESTful",
            "Optimización de Consultas N+1 en Hibernate y Spring Data JPA"
        ]
        LISTA_TEMAS.write_text("\n".join(ejemplos), encoding="utf-8")
        log.info(f"📄 Archivo de temas creado: {LISTA_TEMAS}")
        log.info("ℹ️  Edita el archivo y vuelve a ejecutar.")
        return False
    return True


# ── COMPROBACIÓN DE EXISTENCIA ─────────────────────────────────────────────────
def nombre_archivo(tema: str) -> str:
    """Misma lógica que engine.py para predecir el nombre del .md generado."""
    nombre = tema.lower()
    nombre = re.sub(r'[^\w\s]', '', nombre)
    nombre = re.sub(r'\s+', '_', nombre.strip())
    return nombre[:80] + ".md"


def tema_existe_en_repo(tema: str) -> bool:
    """Busca recursivamente el .md del tema en el repo. Devuelve True si ya existe."""
    if not REPO_ROOT.exists():
        return False
    target = nombre_archivo(tema)
    return any(REPO_ROOT.rglob(target))


# ── EJECUCIÓN DE UN TEMA ───────────────────────────────────────────────────────
def ejecutar_tema(tema: str, modo: str, timeout: int, dry_run: bool) -> bool:
    """
    Lanza racha.py para un tema. Retorna True si éxito.
    - timeout: segundos máximos antes de matar el proceso
    - dry_run: solo imprime el comando, no ejecuta
    """
    cmd = [sys.executable, str(RACHA_SCRIPT), tema]
    if dry_run:
        cmd.append("--dry-run")

    log.info(f"▶ CMD: {' '.join(cmd)}")

    if dry_run:
        # En dry-run mostramos el comando y simulamos éxito
        return True

    try:
        proceso = subprocess.run(
            cmd,
            timeout=timeout   # ← Fix crítico: evita cuelgues infinitos
        )
        return proceso.returncode == 0

    except subprocess.TimeoutExpired:
        log.error(f"⏰ TIMEOUT ({timeout}s) alcanzado para: '{tema}'")
        return False
    except Exception as e:
        log.error(f"❌ Excepción ejecutando '{tema}': {e}")
        return False


# ── RÁFAGA PRINCIPAL ───────────────────────────────────────────────────────────
def ejecutar_rafaga(modo: str, cooldown: int, timeout: int, max_retry: int, dry_run: bool):
    """Orquesta la ráfaga completa con ETA, reintentos y persistencia."""

    if not inicializar_lista():
        return

    if not RACHA_SCRIPT.exists():
        log.error(f"❌ racha.py no encontrado en: {RACHA_SCRIPT}")
        sys.exit(1)

    # Leer y filtrar temas (ignora líneas vacías y comentarios)
    temas = [
        line.strip()
        for line in LISTA_TEMAS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

    if not temas:
        log.warning("⚠️  Lista de temas vacía.")
        return

    total = len(temas)
    # ETA estimada: tiempo_por_tema = timeout + cooldown (worst case)
    eta_total = total * (timeout + cooldown)

    log.info("=" * 60)
    log.info(f"🚀 OpenClaw v9.2 — Modo: {modo.upper()} | Temas: {total}")
    log.info(f"⏱  ETA máxima estimada: {fmt_eta(eta_total)}")
    log.info(f"🔁 Reintentos por tema: {max_retry} | Cooldown: {cooldown}s | Timeout: {timeout}s")
    if dry_run:
        log.info("🔍 DRY-RUN activo — no se ejecutará el motor")
    log.info("=" * 60)

    resultados = {
        "modo": modo,
        "total": total,
        "exitos": 0,
        "fallos": 0,
        "saltados": 0,
        "detalles": []
    }

    tiempo_inicio = time.time()

    for idx, tema in enumerate(temas, 1):
        tiempo_transcurrido = time.time() - tiempo_inicio
        temas_restantes     = total - idx + 1
        eta_restante        = temas_restantes * (timeout + cooldown)

        log.info("\n" + "─" * 60)
        log.info(f"[{idx}/{total}] {tema}")
        log.info(f"⏳ ETA restante: ~{fmt_eta(eta_restante)}")
        log.info("─" * 60)

        if tema_existe_en_repo(tema):
            log.info(f"⏭️  ya existe: '{tema}' — saltando")
            resultados["saltados"] += 1
            resultados["detalles"].append({"tema": tema, "estado": "YA_EXISTE", "intentos": 0})
            continue

        exito = False
        for intento in range(1, max_retry + 1):
            if intento > 1:
                log.warning(f"🔁 Reintento {intento}/{max_retry} para: '{tema}'")
                time.sleep(15)  # pausa corta entre reintentos

            exito = ejecutar_tema(tema, modo, timeout, dry_run)
            if exito:
                break

        if exito:
            log.info(f"✅ OK: '{tema}'")
            resultados["exitos"] += 1
            resultados["detalles"].append({"tema": tema, "estado": "OK", "intentos": intento})
        else:
            log.error(f"❌ FALLO definitivo: '{tema}' tras {max_retry} intento(s)")
            resultados["fallos"] += 1
            resultados["detalles"].append({"tema": tema, "estado": "FALLO", "intentos": intento})

        # Cooldown entre temas (no aplica al último)
        if idx < total:
            log.info(f"❄️  Cooldown {cooldown}s...")
            try:
                time.sleep(cooldown)
            except KeyboardInterrupt:
                log.warning("🛑 Abortado por usuario durante cooldown.")
                break

    # ── RESUMEN ────────────────────────────────────────────────────────────────
    tiempo_total = round((time.time() - tiempo_inicio) / 60, 2)
    tasa_exito   = round(resultados["exitos"] / total * 100, 1) if total else 0

    log.info("\n" + "═" * 60)
    log.info(f"🏁 RÁFAGA COMPLETADA — {tiempo_total} min")
    log.info(f"📊 {resultados['exitos']}/{total} éxitos ({tasa_exito}%) | ⏭️  {resultados['saltados']} ya existían")
    log.info("═" * 60)

    for d in resultados["detalles"]:
        if d["estado"] == "OK":
            icono = "✅"
        elif d["estado"] == "YA_EXISTE":
            icono = "⏭️ "
        else:
            icono = "❌"
        log.info(f"  {icono} [{d['intentos']} int.] {d['tema'][:55]}...")

    guardar_resultados(resultados)


# ── CLI ────────────────────────────────────────────────────────────────────────
def parse_args():
    parser = argparse.ArgumentParser(
        description="OpenClaw v9.2 — Burst Operator para Authority Engine"
    )
    parser.add_argument(
        "--modo", default="std", choices=["std", "deep", "manual"],
        help="Modo de generación (default: std)"
    )
    parser.add_argument(
        "--cooldown", type=int, default=120,
        help="Segundos de enfriamiento entre temas (default: 120)"
    )
    parser.add_argument(
        "--timeout", type=int, default=900,
        help="Timeout máximo por tema en segundos (default: 900)"
    )
    parser.add_argument(
        "--retry", type=int, default=2,
        help="Reintentos automáticos por tema fallido (default: 2)"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Simula la ráfaga sin ejecutar el motor"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    try:
        ejecutar_rafaga(
            modo=args.modo,
            cooldown=args.cooldown,
            timeout=args.timeout,
            max_retry=args.retry,
            dry_run=args.dry_run
        )
    except KeyboardInterrupt:
        log.warning("\n🛑 Ráfaga abortada por usuario (Ctrl+C).")
        sys.exit(0)
