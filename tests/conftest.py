"""Configuración común de pytest para la suite de AuthorityEngine-extract.

Añade la raíz del repo a sys.path para poder hacer `import engine`,
`import cure`, etc. sin instalar el proyecto como paquete ni tocar
requirements.txt de producción.
"""
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
