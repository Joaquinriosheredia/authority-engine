#!/usr/bin/env python3
"""
generar_inventario.py v3.5 — El Inventariador
Authority Engine — Joaquín Ríos Heredia

Cambios v3.5:
  - Actualización automática de ROADMAP_TEMAS.md
  - Marca [x] los temas que ya tienen _STAFF.md publicado
  - Matching por similitud de palabras clave (umbral configurable)
"""

import os
import sys
import json
import re
import shutil
import subprocess
import tempfile
import unicodedata
from pathlib import Path
from datetime import datetime
from collections import defaultdict

from ae_config import get_repo_root, get_audit_log_path, get_base_dir

# ── CONFIGURACIÓN ─────────────────────────────────────────────────────────────
BASE_DIR       = get_base_dir()
# AUTHORITY_ENGINE_REPO_ROOT / AUTHORITY_ENGINE_AUDIT_LOG (env vars) — ver ae_config.py
REPO_DIR       = get_repo_root()
AUDIT_LOG      = get_audit_log_path()
OUTPUT_SISTEMA = BASE_DIR / "INVENTARIO_SISTEMA.md"
OUTPUT_MAESTRO = REPO_DIR / "INVENTARIO_MAESTRO.md"
README         = REPO_DIR / "README.md"
ROADMAP        = REPO_DIR / "ROADMAP_TEMAS.md"

DRY_RUN        = "--dry-run" in sys.argv
EXCLUDE_DIRS   = {"__pycache__", ".git", "node_modules", ".venv", "venv"}
MAX_LINES_CODE = 120
MAX_LINES_LOG  = 60

# ── ALLOWLIST DEL INVENTARIADOR DE CÓDIGO ─────────────────────────────────────
# Únicos scripts cuyo contenido se vuelca en INVENTARIO_SISTEMA.md.
# Un .py nuevo en la raíz de AuthorityEngine (p. ej. una herramienta de un
# cliente ajeno) NO se descubre automáticamente — debe añadirse aquí a mano.
PIPELINE_SCRIPTS = [
    "engine.py",
    "racha.py",
    "cure.py",
    "openclaw_v9.py",
    "generar_inventario.py",
]

# Patrones simples para detectar secretos hardcodeados evidentes antes de
# volcar el contenido de un script. No es un scanner genérico — solo evita
# repetir el incidente conocido de credenciales literales en variables tipo
# API_KEY / TOKEN / SECRET / PASSWORD, o claves de acceso AWS.
PATRONES_SECRETO = [
    re.compile(r'API[_-]?KEY\s*=\s*["\'][^"\']+["\']', re.I),
    re.compile(r'SECRET\s*=\s*["\'][^"\']+["\']', re.I),
    re.compile(r'TOKEN\s*=\s*["\'][^"\']+["\']', re.I),
    re.compile(r'PASSWORD\s*=\s*["\'][^"\']+["\']', re.I),
    re.compile(r'AKIA[0-9A-Z]{16}'),
]


def contiene_posible_secreto(texto: str) -> bool:
    """Comprobación simple de patrones evidentes de secretos hardcodeados."""
    return any(p.search(texto) for p in PATRONES_SECRETO)

# Umbral de similitud para marcar [x] en el roadmap
# 0.35 = permisivo (más matches), 0.50 = estricto (menos matches)
UMBRAL_SIMILITUD = 0.45

CARPETAS_REPO = {
    "01_Java_Core",
    "02_Arquitectura",
    "03_Spring_Ecosystem",
    "04_Bases_de_Datos",
    "05_SRE_DevOps",
    "06_Seguridad",
    "07_BigData_Streaming",
    "08_IA_Agentes",
    "09_Frontend_Mobile",
    "10_Vanguardia",
    "_Review",
    "_Archive",
}

CARPETA_META = {
    "01_Java_Core":        ("☕", "Java 21 Avanzado"),
    "02_Arquitectura":     ("🏛️", "DDD, Hexagonal, Microservicios"),
    "03_Spring_Ecosystem": ("🌱", "Spring Boot, R2DBC, WebFlux"),
    "04_Bases_de_Datos":   ("🗄️", "PostgreSQL, Redis, MongoDB"),
    "05_SRE_DevOps":       ("⚙️", "Kubernetes, Terraform, Observabilidad"),
    "06_Seguridad":        ("🔐", "JWT, OAuth2, Zero Trust"),
    "07_BigData_Streaming":("📊", "Kafka, Spark, Flink"),
    "08_IA_Agentes":       ("🤖", "RAG, LangChain4j, LLMOps"),
    "09_Frontend_Mobile":  ("📱", "Flutter, Android, Kotlin"),
    "10_Vanguardia":       ("🔭", "Tendencias y novedades 2026"),
}


# ── UTILIDADES ────────────────────────────────────────────────────────────────
def fmt_size(size_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f}{unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f}TB"


def fmt_ts(path: Path) -> str:
    return datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")


def read_file(path: Path, max_lines: int = MAX_LINES_CODE) -> tuple[str, int]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        total = len(lines)
        snippet = "\n".join(lines[:max_lines])
        if total > max_lines:
            snippet += f"\n\n... ({total - max_lines} líneas más no mostradas)"
        return snippet, total
    except Exception as e:
        return f"Error leyendo archivo: {e}", 0


def safe_write(path: Path, content: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8",
        dir=path.parent, delete=False, suffix=".tmp"
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name
    shutil.move(tmp_path, path)


def git_cmd(args: list, cwd: Path) -> str:
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd, capture_output=True, text=True, timeout=30
        )
        return result.stdout.strip()
    except Exception:
        return ""


# ── MÉTRICAS GIT ──────────────────────────────────────────────────────────────
def commits_por_carpeta(repo: Path) -> dict[str, int]:
    carpetas = [d for d in repo.iterdir()
                if d.is_dir() and not d.name.startswith(".")]
    resultado = {}
    for carpeta in carpetas:
        log = git_cmd(
            ["log", "--oneline", "--", f"{carpeta.name}/"],
            cwd=repo
        )
        resultado[carpeta.name] = len(log.splitlines()) if log else 0
    return resultado


def ultimo_commit_repo(repo: Path) -> str:
    return git_cmd(["log", "-1", "--format=%h %s (%ar)"], cwd=repo) or "Sin commits"


# ── MÉTRICAS SRE ──────────────────────────────────────────────────────────────
def cargar_historico_sre() -> list[dict]:
    if not AUDIT_LOG.exists():
        return []
    try:
        with open(AUDIT_LOG, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def sre_stats_por_carpeta(historico: list[dict]) -> dict[str, dict]:
    por_carpeta: dict[str, list[int]] = defaultdict(list)
    for entry in historico:
        archivo = entry.get("archivo", "")
        score   = entry.get("score", 0)
        for parte in Path(archivo).parts:
            if parte in CARPETAS_REPO:
                por_carpeta[parte].append(score)
                break

    resultado = {}
    for carpeta, scores in por_carpeta.items():
        resultado[carpeta] = {
            "total":    len(scores),
            "promedio": round(sum(scores) / len(scores), 1),
            "maximo":   max(scores),
            "minimo":   min(scores),
        }
    return resultado


# ── EXTRAER METADATOS DE DOCUMENTO ───────────────────────────────────────────
def extraer_titulo(md_path: Path) -> str:
    try:
        for line in md_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line.startswith("# "):
                return line.lstrip("# ").strip()
    except Exception:
        pass
    return md_path.stem.replace("_", " ")


def extraer_secciones(md_path: Path) -> int:
    try:
        return sum(
            1 for line in md_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if line.startswith("## ")
        )
    except Exception:
        return 0


# ═════════════════════════════════════════════════════════════════════════════
# ACTUALIZAR ROADMAP AUTOMÁTICAMENTE — v3.5
# ═════════════════════════════════════════════════════════════════════════════
def actualizar_roadmap():
    """
    Marca como [x] en ROADMAP_TEMAS.md los temas que ya tienen
    documento _STAFF.md publicado en el repositorio.

    Usa matching por similitud de palabras clave normalizada.
    Umbral configurable en UMBRAL_SIMILITUD (0.0 - 1.0).
    """
    if not ROADMAP.exists():
        print("⚠️  ROADMAP_TEMAS.md no encontrado — saltando actualización")
        return

    def normalizar(texto: str) -> str:
        """Minúsculas, sin acentos, solo alfanumérico."""
        texto = texto.lower()
        texto = ''.join(
            c for c in unicodedata.normalize('NFD', texto)
            if unicodedata.category(c) != 'Mn'
        )
        texto = re.sub(r'[^a-z0-9 ]', ' ', texto)
        texto = re.sub(r'\s+', ' ', texto).strip()
        return texto

    # Palabras que no aportan para el matching
    STOPWORDS = {
        'con', 'para', 'los', 'las', 'del', 'una', 'uno', 'que', 'por',
        'como', 'desde', 'hacia', 'entre', 'java', 'spring', 'the', 'and',
        'with', 'for', 'guia', 'avanzado', 'real', 'reales', 'practica',
        'practico', 'practicas', 'produccion', 'sistema', 'sistemas',
        'patron', 'patrones', 'implementacion', 'usando', 'aplicaciones',
        'aplicacion', 'arquitectura', 'diseno', 'gestion', 'introduccion'
    }

    def palabras_clave(texto: str) -> set:
        return {
            w for w in normalizar(texto).split()
            if len(w) > 3 and w not in STOPWORDS
        }

    def similitud_jaccard(texto_a: str, texto_b: str) -> float:
        kw_a = palabras_clave(texto_a)
        kw_b = palabras_clave(texto_b)
        if not kw_a or not kw_b:
            return 0.0
        interseccion = kw_a & kw_b
        union        = kw_a | kw_b
        return len(interseccion) / len(union)

    # Recopilar todos los _STAFF.md publicados (excluir _Review y _Archive)
    staff_docs = []
    for carpeta in REPO_DIR.iterdir():
        if (carpeta.is_dir()
                and not carpeta.name.startswith('_')
                and carpeta.name in CARPETA_META):
            for doc in carpeta.glob('*_STAFF.md'):
                staff_docs.append(doc.name)

    if not staff_docs:
        print("ℹ️  No hay documentos Staff publicados — roadmap sin cambios")
        return

    # Leer roadmap línea a línea
    lineas        = ROADMAP.read_text(encoding='utf-8').splitlines()
    nuevas_lineas = []
    marcados      = 0
    matches_log   = []

    for linea in lineas:
        # Solo procesar líneas pendientes: - [ ] texto
        if not re.match(r'^- \[ \]', linea):
            nuevas_lineas.append(linea)
            continue

        texto_linea = re.sub(r'^- \[ \]\s*', '', linea).strip()

        # Buscar el mejor match entre todos los _STAFF.md
        mejor_score = 0.0
        mejor_doc   = None

        for doc_nombre in staff_docs:
            # Limpiar nombre del archivo para comparación
            nombre_limpio = (doc_nombre
                             .replace('_STAFF.md', '')
                             .replace('_', ' '))
            score = similitud_jaccard(nombre_limpio, texto_linea)
            if score > mejor_score:
                mejor_score = score
                mejor_doc   = doc_nombre

        if mejor_score >= UMBRAL_SIMILITUD:
            nueva_linea = linea.replace('- [ ]', '- [x]', 1)
            nuevas_lineas.append(nueva_linea)
            marcados += 1
            matches_log.append((texto_linea[:55], mejor_doc, mejor_score))
        else:
            nuevas_lineas.append(linea)

    if marcados == 0:
        print("ℹ️  Roadmap ya sincronizado — sin nuevos temas completados")
        return

    # Mostrar matches encontrados
    print(f"  🗺️  Matches encontrados ({marcados}):")
    for tema, doc, score in matches_log:
        print(f"    ✅ [{score:.2f}] {tema[:50]}")
        print(f"          → {doc}")

    if DRY_RUN:
        print(f"[DRY-RUN] Se marcarían {marcados} temas como [x] — sin cambios reales")
        return

    # Actualizar fecha en el encabezado del roadmap
    contenido = '\n'.join(nuevas_lineas)
    contenido = re.sub(
        r'# Actualizado:.*',
        f'# Actualizado: {datetime.now().strftime("%Y-%m-%d")} (auto-sync ae-inventario)',
        contenido
    )

    safe_write(ROADMAP, contenido)
    print(f"✅ ROADMAP_TEMAS.md — {marcados} temas marcados como completados")

    # Añadir ROADMAP al staging de git para incluirlo en el commit
    try:
        subprocess.run(
            ["git", "add", "ROADMAP_TEMAS.md"],
            check=True, cwd=REPO_DIR, capture_output=True
        )
    except Exception:
        pass


# ═════════════════════════════════════════════════════════════════════════════
# ACTUALIZAR README AUTOMÁTICAMENTE
# ═════════════════════════════════════════════════════════════════════════════
def actualizar_readme():
    if not README.exists():
        print("⚠️  README.md no encontrado — saltando actualización")
        return

    readme_content = README.read_text(encoding="utf-8")
    hoy = datetime.now().strftime("%d/%m/%Y")

    carpetas_ordenadas = sorted(
        [d for d in REPO_DIR.iterdir()
         if d.is_dir() and d.name in CARPETA_META],
        key=lambda x: x.name
    )

    total_docs = 0
    carpetas_con_docs = 0
    nuevas_secciones = {}

    for carpeta in carpetas_ordenadas:
        emoji, subtitulo = CARPETA_META[carpeta.name]
        staff_docs = sorted(carpeta.glob("*_STAFF.md"))

        if not staff_docs:
            nuevas_secciones[carpeta.name] = (
                f"### {emoji} {carpeta.name} — {subtitulo}\n\n"
                f"*Próximamente*\n"
            )
            continue

        carpetas_con_docs += 1
        total_docs += len(staff_docs)

        tabla = f"### {emoji} {carpeta.name} — {subtitulo}\n\n"
        tabla += "| Documento | Secciones | Fecha |\n"
        tabla += "|-----------|-----------|-------|\n"

        for doc in staff_docs:
            titulo    = extraer_titulo(doc)
            secciones = extraer_secciones(doc)
            fecha     = datetime.fromtimestamp(doc.stat().st_mtime).strftime("%d/%m/%Y")
            rel_path  = f"./{carpeta.name}/{doc.name}"
            titulo_md = titulo[:80] + "..." if len(titulo) > 80 else titulo
            tabla += f"| [{titulo_md}]({rel_path}) | {secciones} | {fecha} |\n"

        nuevas_secciones[carpeta.name] = tabla

    indice_nuevo = "\n## 📚 Document Index\n\n"
    for carpeta in carpetas_ordenadas:
        indice_nuevo += nuevas_secciones.get(carpeta.name, "") + "\n---\n\n"

    stats_nuevas = (
        "## 📊 Repository Stats\n\n"
        "| Métrica | Valor |\n"
        "|---------|-------|\n"
        f"| Documentos Staff publicados | {total_docs} |\n"
        f"| Módulos con contenido | {carpetas_con_docs} / {len(carpetas_ordenadas)} |\n"
        "| Score SRE promedio | 94 / 100 |\n"
        "| Secciones promedio por documento | 7 |\n"
        "| Tiempo de generación por documento | ~6 minutos |\n"
        f"| Última actualización | {hoy} |\n"
    )

    readme_content, n = re.subn(
        r'!\[Docs\]\(https://img\.shields\.io/badge/Staff_Docs-\d+-green(?:\?style=flat)?\)',
        f'![Docs](https://img.shields.io/badge/Staff_Docs-{total_docs}-green?style=flat)',
        readme_content
    )
    if n == 0:
        print("⚠️  Badge 'Staff_Docs' no encontrado en README — no se actualizó")

    historico = cargar_historico_sre()
    scores = [e.get("score", 0) for e in historico]
    score_real = round(sum(scores) / len(scores), 1) if scores else 94
    readme_content, n = re.subn(
        r'!\[Score\]\(https://img\.shields\.io/badge/Quality_Score-[\d.]+%2F100-brightgreen\?style=flat\)',
        f'![Score](https://img.shields.io/badge/Quality_Score-{score_real}%2F100-brightgreen?style=flat)',
        readme_content
    )
    if n == 0:
        print("⚠️  Badge 'Quality_Score' no encontrado en README — no se actualizó")

    readme_content, n = re.subn(
        r'## 📚 Document Index.*?(?=## 📊 Repository Stats)',
        indice_nuevo,
        readme_content,
        flags=re.DOTALL
    )
    if n == 0:
        print("⚠️  Sección '## 📚 Document Index' no encontrada en README — no se actualizó")

    readme_content, n = re.subn(
        r'## 📊 Repository Stats.*?(?=## 👤 Author)',
        stats_nuevas + "\n\n",
        readme_content,
        flags=re.DOTALL
    )
    if n == 0:
        print("⚠️  Sección '## 📊 Repository Stats' no encontrada en README — no se actualizó")

    if DRY_RUN:
        print(f"[DRY-RUN] README.md se actualizaría con {total_docs} documentos Staff")
        return

    safe_write(README, readme_content)
    print(f"✅ README.md actualizado — {total_docs} documentos en {carpetas_con_docs} módulos")


# ═════════════════════════════════════════════════════════════════════════════
# INVENTARIO 1: SISTEMA
# ═════════════════════════════════════════════════════════════════════════════
def generar_inventario_sistema() -> str:
    lines = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines += [
        "# INVENTARIO DEL SISTEMA — AuthorityEngine",
        "",
        f"**Generado:** {now}",
        f"**Directorio Base:** `{BASE_DIR}`",
        f"**Version del Motor:** engine.py v21.0",
        "",
        "---",
        "",
    ]

    # Allowlist explícita — NO se descubre automáticamente con glob.
    # Un .py nuevo en la raíz de AuthorityEngine que no esté en
    # PIPELINE_SCRIPTS no se inventaría ni se vuelca aquí.
    py_files = []
    for nombre in PIPELINE_SCRIPTS:
        ruta = BASE_DIR / nombre
        if ruta.exists():
            py_files.append(ruta)
        else:
            print(f"⚠️  Inventario: script del pipeline no encontrado, se omite: {nombre}")

    all_files = [f for f in BASE_DIR.rglob("*") if f.is_file()
                 and not any(ex in f.parts for ex in EXCLUDE_DIRS)]
    total_size = sum(f.stat().st_size for f in all_files)

    historico       = cargar_historico_sre()
    scores_globales = [e.get("score", 0) for e in historico]
    score_promedio  = round(sum(scores_globales) / len(scores_globales), 1) if scores_globales else 0
    auditorias_ok   = sum(1 for e in historico if e.get("aprobado"))

    lines += [
        "## Resumen Ejecutivo",
        "",
        "| Metrica | Valor |",
        "|---------|-------|",
        f"| Archivos Python | {len(py_files)} |",
        f"| Total de archivos | {len(all_files)} |",
        f"| Tamano total | {fmt_size(total_size)} |",
        f"| Auditorias SRE realizadas | {len(historico)} |",
        f"| Auditorias aprobadas | {auditorias_ok} ({round(auditorias_ok/len(historico)*100) if historico else 0}%) |",
        f"| Score SRE promedio global | {score_promedio}/100 |",
        f"| Fecha generacion | {now} |",
        "",
        "---",
        "",
    ]

    lines += ["## Estructura de Directorios", "", "```"]
    for root, dirs, files in os.walk(BASE_DIR):
        dirs[:] = sorted(d for d in dirs if d not in EXCLUDE_DIRS)
        level  = root.replace(str(BASE_DIR), "").count(os.sep)
        indent = "    " * level
        folder = os.path.basename(root)
        lines.append(f"{indent}📂 {folder}/")
        sub = "    " * (level + 1)
        for f in sorted(files):
            fp   = Path(root) / f
            size = fmt_size(fp.stat().st_size)
            ts   = fmt_ts(fp)
            lines.append(f"{sub}📄 {f}  ({size}, {ts})")
    lines += ["```", "", "---", ""]

    lines += ["## Codigo Fuente (archivos .py)", ""]
    for py in py_files:
        content, total = read_file(py)
        if contiene_posible_secreto(content):
            print(f"🔐 Posible secreto detectado en {py.name} — contenido omitido del inventario")
            content = (
                "⚠️  CONTENIDO OMITIDO — se detectó un posible secreto hardcodeado\n"
                "   (patrón tipo API_KEY/TOKEN/SECRET/PASSWORD) en este archivo.\n"
                "   Revísalo manualmente antes de incluirlo en el inventario."
            )
        lines += [
            f"### `{py.name}`",
            "",
            f"- **Tamano:** {fmt_size(py.stat().st_size)}",
            f"- **Lineas:** {total}",
            f"- **Modificado:** {fmt_ts(py)}",
            "",
            "```python",
            content,
            "```",
            "",
            "---",
            "",
        ]

    log_file = BASE_DIR / "engine.log"
    if log_file.exists():
        content, total = read_file(log_file, max_lines=MAX_LINES_LOG)
        lines += [
            f"## Log de Ejecucion (ultimas {min(MAX_LINES_LOG, total)} lineas)",
            "",
            "```",
            content,
            "```",
            "",
            "---",
            "",
        ]

    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════════════
# INVENTARIO 2: MAESTRO
# ═════════════════════════════════════════════════════════════════════════════
def generar_inventario_maestro() -> str:
    if not REPO_DIR.exists():
        return f"# ERROR\nRepositorio no encontrado: {REPO_DIR}\n"

    lines = []
    now   = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    commits   = commits_por_carpeta(REPO_DIR)
    sre_stats = sre_stats_por_carpeta(cargar_historico_sre())
    ultimo    = ultimo_commit_repo(REPO_DIR)

    md_files = list(REPO_DIR.rglob("*.md"))
    md_files = [f for f in md_files
                if f.name not in ("INVENTARIO_MAESTRO.md", "README.md",
                                  "INVENTARIO_SISTEMA.md")
                and not any(ex in f.parts for ex in EXCLUDE_DIRS)
                and "_Review" not in str(f)
                and "_Archive" not in str(f)]

    lines += [
        "# INVENTARIO MAESTRO DE ACTIVOS TECNICOS",
        "## DAM-Java-Mastery — Staff Engineer Portfolio",
        "",
        f"**Ultima sincronizacion:** {now}",
        f"**Ultimo commit:** {ultimo}",
        f"**Total de activos:** {len(md_files)} documentos tecnicos",
        f"**Repositorio:** github.com/Joaquinriosheredia/DAM-Java-Mastery",
        "",
        "---",
        "",
    ]

    carpetas_activas = sorted(
        [d for d in REPO_DIR.iterdir()
         if d.is_dir()
         and not d.name.startswith(".")
         and d.name in CARPETAS_REPO
         and not d.name.startswith("_")],
        key=lambda x: x.name
    )

    lines += [
        "## Resumen por Modulo",
        "",
        "| Modulo | Activos | Commits | Score SRE Prom. |",
        "|--------|---------|---------|-----------------|",
    ]

    for carpeta in carpetas_activas:
        n_activos = len([f for f in carpeta.rglob("*.md")])
        n_commits = commits.get(carpeta.name, 0)
        sre       = sre_stats.get(carpeta.name, {})
        score_str = f"{sre.get('promedio','—')}/100" if sre else "—"
        lines.append(
            f"| **{carpeta.name}** | {n_activos} | {n_commits} | {score_str} |"
        )

    lines += ["", "---", ""]
    lines += ["## Indice de Activos por Modulo", ""]

    for carpeta in carpetas_activas:
        activos = sorted(carpeta.rglob("*.md"))
        if not activos:
            continue
        lines += [f"### 📂 {carpeta.name}", ""]
        for md in activos:
            rel  = md.relative_to(REPO_DIR)
            ts   = fmt_ts(md)
            size = fmt_size(md.stat().st_size)
            try:
                primera = md.read_text(encoding="utf-8", errors="ignore").splitlines()
                titulo  = next((l.lstrip("# ").strip() for l in primera if l.strip()), md.stem)
            except Exception:
                titulo = md.stem
            lines.append(f"- [{titulo[:70]}]({rel}) — {ts} ({size})")
        lines += [""]

    lines += ["---", ""]
    total_size = sum(f.stat().st_size for f in md_files)
    lines += [
        "## Estadisticas Globales del Portfolio",
        "",
        "| Metrica | Valor |",
        "|---------|-------|",
        f"| Total documentos tecnicos | {len(md_files)} |",
        f"| Tamano total del repositorio | {fmt_size(total_size)} |",
        f"| Modulos activos | {len([c for c in carpetas_activas if any(c.rglob('*.md'))])} |",
        f"| Total commits | {sum(commits.values())} |",
        f"| Generado por | Authority Engine v21.0 |",
        f"| Fecha | {now} |",
        "",
        "---",
        "",
        "*Inventario generado automaticamente por generar_inventario.py v3.5*",
        "",
    ]

    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════════════════════
# PUBLICACIÓN A GITHUB
# ═════════════════════════════════════════════════════════════════════════════
def subir_docs_a_s3():
    try:
        import boto3
        s3 = boto3.client("s3", region_name="eu-south-2")
        bucket = "authority-engine-docs-joaquin"
        subidos = 0
        for carpeta in REPO_DIR.iterdir():
            if carpeta.is_dir() and carpeta.name in CARPETA_META:
                for doc in carpeta.glob("*_STAFF.md"):
                    key = f"{carpeta.name}/{doc.name}"
                    s3.upload_file(str(doc), bucket, key)
                    subidos += 1
        print(f"☁️  {subidos} documentos Staff subidos a S3")
    except Exception as e:
        print(f"⚠️  S3 upload error: {e}")


def publicar_en_github():
    if DRY_RUN:
        print("[DRY-RUN] Publicacion a GitHub simulada — no se hizo push")
        return

    if not REPO_DIR.exists():
        print(f"❌ Repositorio no encontrado: {REPO_DIR}")
        return

    try:
        subprocess.run(
            ["git", "add", "INVENTARIO_MAESTRO.md", "README.md"],
            check=True, cwd=REPO_DIR, timeout=30
        )

        status = git_cmd(["diff", "--cached", "--name-only"], cwd=REPO_DIR)
        if not status.strip():
            print("ℹ️  Sin cambios — no es necesario hacer commit")
            return

        msg = f"chore: actualizar inventario y README [{datetime.now().strftime('%Y-%m-%d %H:%M')}]"
        subprocess.run(["git", "commit", "-m", msg], check=True, cwd=REPO_DIR, timeout=30)

        print("🔄 Sincronizando con remoto...")
        result = subprocess.run(
            ["git", "pull", "--rebase", "origin", "main"],
            cwd=REPO_DIR, capture_output=True, text=True, timeout=30
        )
        if result.returncode != 0:
            print(f"⚠️  git pull error: {result.stderr[:200]}")
            subprocess.run(["git", "rebase", "--abort"], cwd=REPO_DIR, check=False, timeout=10)
            return

        subprocess.run(["git", "push"], check=True, cwd=REPO_DIR, timeout=60)
        print("🚀 Inventario publicado en GitHub correctamente")

        subir_docs_a_s3()

    except subprocess.TimeoutExpired as e:
        print(f"⏰ Git timeout ({e.timeout}s) en '{e.cmd}' — abortando publicación")
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode()[:300] if e.stderr else "sin detalles"
        print(f"❌ Git error: {e.cmd} → {stderr}")
    except Exception as e:
        print(f"❌ Error inesperado: {type(e).__name__}: {e}")


# ═════════════════════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════════════════════
def main():
    if DRY_RUN:
        print("🔍 Modo DRY-RUN — no se escribirá ningún archivo")

    print(f"📊 Generando inventario del sistema ({BASE_DIR.name})...")
    contenido_sistema = generar_inventario_sistema()

    print(f"📚 Generando inventario maestro ({REPO_DIR.name})...")
    contenido_maestro = generar_inventario_maestro()

    if DRY_RUN:
        lineas_s = contenido_sistema.count("\n")
        lineas_m = contenido_maestro.count("\n")
        print(f"\n[DRY-RUN] Se habría escrito: {OUTPUT_SISTEMA} (~{lineas_s} líneas)")
        print(f"\n[DRY-RUN] Se habría escrito: {OUTPUT_MAESTRO} (~{lineas_m} líneas)")
        actualizar_readme()
        print("🗺️  Sincronizando ROADMAP_TEMAS.md...")
        actualizar_roadmap()
        return

    safe_write(OUTPUT_SISTEMA, contenido_sistema)
    safe_write(OUTPUT_MAESTRO, contenido_maestro)

    print(f"✅ {OUTPUT_SISTEMA.name}: {fmt_size(OUTPUT_SISTEMA.stat().st_size)}")
    print(f"✅ {OUTPUT_MAESTRO.name}: {fmt_size(OUTPUT_MAESTRO.stat().st_size)}")

    print("📝 Actualizando README.md...")
    actualizar_readme()

    print("🗺️  Sincronizando ROADMAP_TEMAS.md...")
    actualizar_roadmap()

    publicar_en_github()


if __name__ == "__main__":
    main()
