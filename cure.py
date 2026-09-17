#!/usr/bin/env python3
"""
cure.py v3.0 — Cirujano de Inyección con flujo Review
Authority Engine — Joaquín Ríos Heredia

Cambios v3.0:
- Reemplaza el documento completo en lugar de inyectar sección a sección
- Más robusto: funciona con cualquier estructura que venga de Claude
- Mantiene los metadatos PATH_LOCAL y CATEGORIA del original
- Backup, diff, score y git push sin cambios
"""

import re
import sys
import shutil
import difflib
from pathlib import Path
import subprocess
import os

try:
    from engine import evaluar, CONFIG, log
except ImportError as e:
    print(f"❌ No se pudo importar engine.py: {e}")
    print("   Ejecuta cure.py desde el directorio del repo (junto a engine.py)")
    sys.exit(1)

REPO_ROOT = Path(CONFIG["REPO_ROOT"])


# ── Git ────────────────────────────────────────────────────────────────────────

def git_push_definitivo(path: Path, tema: str, score: int, categoria: str) -> bool:
    try:
        os.chdir(REPO_ROOT)

        result = subprocess.run(
            ["git", "pull", "--rebase"],
            capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            log("⚠️  git pull conflicto — abortando rebase")
            subprocess.run(["git", "rebase", "--abort"], check=False, timeout=10)
            return False

        subprocess.run(["git", "add", str(path)], check=True, timeout=30)
        subprocess.run(["git", "commit", "-m",
            f"feat: {tema} [{categoria}] (Score:{score}) — revisado por Claude"],
            check=True, timeout=30)
        subprocess.run(["git", "push"], check=True, timeout=60)

        log(f"✅ Publicado en {categoria}/ en GitHub")
        return True
    except subprocess.TimeoutExpired as e:
        log(f"⏰ Git timeout ({e.timeout}s) en '{e.cmd}' — abortando publicación")
        return False
    except Exception as e:
        log(f"⚠️  Git fallo: {e}")
        return False


# ── Backup ────────────────────────────────────────────────────────────────────

def crear_backup(path: Path) -> Path:
    backup = path.with_suffix(".md.bak")
    shutil.copy2(path, backup)
    return backup

def restaurar_backup(path: Path, backup: Path):
    shutil.copy2(backup, path)
    log(f"↩  Restaurado desde {backup.name}")


# ── Extracción de metadatos ───────────────────────────────────────────────────

def extraer_path(texto: str) -> Path | None:
    m = re.search(r"PATH_LOCAL:\s*(.+)", texto)
    if not m:
        return None
    return Path(m.group(1).strip())

def extraer_categoria(texto: str) -> str:
    m = re.search(r"CATEGORIA:\s*(.+)", texto)
    if m:
        return m.group(1).strip()
    return "10_Vanguardia"

def extraer_tema(texto: str) -> str:
    m = re.search(r"^#\s+(.+)", texto, re.M)
    if m:
        return m.group(1).strip()
    return "documento"

def nombre_archivo(tema: str) -> str:
    nombre = tema.lower()
    nombre = re.sub(r'[^\w\s]', '', nombre)
    nombre = re.sub(r'\s+', '_', nombre.strip())
    return nombre[:80] + "_STAFF.md"


# ── Preparar documento final ──────────────────────────────────────────────────

def preparar_documento(contenido_claude: str, path_original: Path) -> str:
    """
    Toma el documento refinado por Claude y asegura que tenga
    los metadatos correctos (PATH_LOCAL, CATEGORIA, Score).
    Reemplaza el contenido completo — no inyecta sección a sección.
    """
    # Extraer metadatos del documento de Claude
    categoria = extraer_categoria(contenido_claude)
    tema = extraer_tema(contenido_claude)

    # Evaluar el score del contenido refinado
    score, _ = evaluar(contenido_claude)

    # Construir cabecera de metadatos limpia
    cabecera = (
        f"# {tema}\n\n"
        f"PATH_LOCAL: {path_original}\n"
        f"CATEGORIA: {categoria}\n"
        f"Score: {score}\n\n"
        f"---\n\n"
    )

    # Eliminar cualquier cabecera de metadatos existente en el documento de Claude
    # y quedarnos solo con el contenido a partir del primer ## 
    contenido_limpio = re.sub(
        r'^.*?(?=^## )',
        '',
        contenido_claude,
        count=1,
        flags=re.S | re.M
    )

    return cabecera + contenido_limpio.strip() + "\n"


# ── Diff ──────────────────────────────────────────────────────────────────────

def mostrar_diff(original: str, nuevo: str, nombre: str) -> bool:
    diff = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        nuevo.splitlines(keepends=True),
        fromfile=f"{nombre} (borrador)",
        tofile=f"{nombre} (claude)",
        n=2,
    ))

    if not diff:
        print("   ⚪ Sin cambios detectados.")
        return False

    print(f"\n{'─'*60}")
    print(f"DIFF — {nombre}")
    print('─'*60)
    for linea in diff[:150]:
        print(linea, end="")
    if len(diff) > 150:
        print(f"\n   … {len(diff)-150} líneas más …")
    print(f"\n{'─'*60}")

    resp = input("¿Aplicar cambios? [s/N] ").strip().lower()
    return resp in ("s", "si", "sí", "y", "yes")


# ── Procesador principal ──────────────────────────────────────────────────────

def procesar(contenido_claude: str):
    # 1. Extraer metadatos
    path = extraer_path(contenido_claude)
    if not path or not path.exists():
        print(f"⚠️  Archivo no encontrado: {path}")
        print("   Asegúrate de que el documento tiene PATH_LOCAL: con la ruta correcta")
        sys.exit(1)

    categoria = extraer_categoria(contenido_claude)
    tema = extraer_tema(contenido_claude)
    nombre = path.name

    log(f"📄 Procesando: {nombre}")
    log(f"📂 Categoría destino: {categoria}")

    # 2. Backup del original
    backup = crear_backup(path)
    texto_original = path.read_text(encoding="utf-8")

    # 3. Preparar documento final completo
    texto_final = preparar_documento(contenido_claude, path)

    # 4. Evaluar score
    score, errores = evaluar(texto_final)
    log(f"📊 Score tras refinado: {score}")

    if score <= 50:
        print(f"❌ Score {score} demasiado bajo {errores} — archivo sin modificar")
        return

    # 5. Mostrar diff y confirmar
    if not mostrar_diff(texto_original, texto_final, nombre):
        log("↩  Sin cambios aplicados")
        return

    # 6. Escribir archivo refinado
    try:
        path.write_text(texto_final, encoding="utf-8")
        log(f"✅ Archivo actualizado. Score: {score}")
    except OSError as e:
        print(f"❌ Error escribiendo: {e}")
        restaurar_backup(path, backup)
        return

    # 7. Publicar o dejar en _Review
    if score >= CONFIG["SCORE_DEPLOY"]:
        destino_dir = REPO_ROOT / categoria
        destino_dir.mkdir(parents=True, exist_ok=True)

        nombre_limpio = nombre_archivo(tema)
        destino_path = destino_dir / nombre_limpio

        shutil.move(str(path), str(destino_path))
        log(f"📦 Movido a: {categoria}/{nombre_limpio}")

        # Limpiar carpeta _Review del tema si queda vacía
        try:
            path.parent.rmdir()
        except:
            pass

        git_push_definitivo(destino_path, tema, score, categoria)

        print(f"\n{'━'*60}")
        print(f"🚀 PUBLICADO EN GITHUB")
        print(f"   Carpeta: {categoria}/")
        print(f"   Archivo: {nombre_limpio}")
        print(f"   Score:   {score}/100")
        print(f"{'━'*60}\n")

    else:
        log(f"⚠️  Score {score} < {CONFIG['SCORE_DEPLOY']} — se queda en _Review/")
        print(f"\n   Documento en _Review/ con score {score}. Necesita más trabajo.")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("📋 Pega el documento refinado por Claude y pulsa CTRL+D:\n")
    data = sys.stdin.read()
    if not data.strip():
        print("❌ No se recibió contenido.")
        sys.exit(1)
    procesar(data)
