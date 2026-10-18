#!/usr/bin/env python3
"""Convert all PDF files in a directory to Markdown files using MarkItDown.

The script scans only the selected directory (non-recursive), preserving each
input filename and changing only the extension to .md in a separate output
subdirectory.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

#Script realizado por el Profesor Cristian Pacifico
def convert_with_python_api(pdf_path: Path) -> str:
    """Convert a PDF to markdown text using the markitdown Python API."""
    try:
        from markitdown import MarkItDown
    except ImportError as exc:
        raise RuntimeError(
            "No se pudo importar 'markitdown'. Instala el paquete en este entorno."
        ) from exc

    converter = MarkItDown()
    result = converter.convert(str(pdf_path))
    return result.text_content


def convert_with_cli(pdf_path: Path) -> str:
    """Convert a PDF to markdown text using the markitdown CLI (stdout)."""
    markitdown_bin = shutil.which("markitdown")
    if not markitdown_bin:
        raise RuntimeError("No se encontro el ejecutable 'markitdown' en PATH.")

    completed = subprocess.run(
        [markitdown_bin, str(pdf_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout


def convert_pdf(pdf_path: Path) -> str:
    """Try API first, then CLI as fallback."""
    try:
        return convert_with_python_api(pdf_path)
    except Exception:
        return convert_with_cli(pdf_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Convierte todos los PDF de un directorio a Markdown y guarda los .md "
            "en un subdirectorio aparte."
        )
    )
    parser.add_argument(
        "input_dir",
        nargs="?",
        default=".",
        help="Directorio con PDFs (por defecto: directorio actual).",
    )
    parser.add_argument(
        "-o",
        "--output-subdir",
        default="md_llm",
        help="Nombre del subdirectorio de salida dentro de input_dir (por defecto: md).",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    input_dir = Path(args.input_dir).expanduser().resolve()
    if not input_dir.is_dir():
        print(f"Error: no existe el directorio: {input_dir}", file=sys.stderr)
        return 1

    output_dir = input_dir / args.output_subdir
    output_dir.mkdir(parents=True, exist_ok=True)

    pdf_files = sorted(path for path in input_dir.iterdir() if path.suffix.lower() == ".pdf")
    if not pdf_files:
        print(f"No se encontraron PDF en: {input_dir}")
        return 0

    converted = 0
    failed = 0

    for pdf_path in pdf_files:
        output_md = output_dir / f"{pdf_path.stem}.md"
        print(f"Convirtiendo: {pdf_path.name} -> {output_md.name}")
        try:
            markdown_text = convert_pdf(pdf_path)
            output_md.write_text(markdown_text, encoding="utf-8")
            converted += 1
        except Exception as exc:
            failed += 1
            print(f"  Error en {pdf_path.name}: {exc}", file=sys.stderr)

    print(f"\nListo. Convertidos: {converted} | Fallidos: {failed} | Salida: {output_dir}")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
