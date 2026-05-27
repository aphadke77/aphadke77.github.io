#!/usr/bin/env python3
"""
docx_converter.py — Convert .docx files to PDF and/or HTML.

Usage (local macOS):
    python3 docx_converter.py                          # convert all .docx in cwd
    python3 docx_converter.py --formats pdf            # PDF only
    python3 docx_converter.py --formats html           # HTML only
    python3 docx_converter.py --formats pdf,html       # both (default)
    python3 docx_converter.py --output-dir converted   # put results in ./converted/
    python3 docx_converter.py report.docx memo.docx    # specific files

macOS setup (one-time):
    brew install pandoc
    brew install --cask libreoffice        # needed for PDF output

GitHub Actions: pandoc + libreoffice are installed by the workflow automatically.
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path


# ── helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: list[str], label: str) -> bool:
    """Run a subprocess; return True on success, print error on failure."""
    try:
        result = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        print(f"    ERROR [{label}]: {exc.stderr.strip() or exc.stdout.strip()}")
        return False
    except FileNotFoundError:
        print(f"    ERROR: '{cmd[0]}' not found. See setup instructions in script header.")
        return False


def _check_tool(name: str, install_hint: str) -> bool:
    if shutil.which(name):
        return True
    print(f"  WARNING: '{name}' not found. {install_hint}")
    return False


# ── converters ───────────────────────────────────────────────────────────────

def to_html(docx: Path, output_dir: Path, verbose: bool) -> Path | None:
    """Convert docx → self-contained HTML via pandoc."""
    out = output_dir / (docx.stem + ".html")
    cmd = [
        "pandoc",
        str(docx),
        "--from=docx",
        "--to=html5",
        "--standalone",
        "--self-contained",       # embed CSS/images inline
        "--metadata", f"title={docx.stem}",
        "--output", str(out),
    ]
    if verbose:
        print(f"    pandoc: {docx.name} → {out.name}")
    if _run(cmd, "pandoc html"):
        return out
    return None


def to_pdf_libreoffice(docx: Path, output_dir: Path, verbose: bool) -> Path | None:
    """Convert docx → PDF via LibreOffice headless (best formatting fidelity)."""
    # LibreOffice writes <stem>.pdf into output_dir
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        print("    ERROR: LibreOffice not found. macOS: brew install --cask libreoffice")
        return None

    cmd = [
        soffice,
        "--headless",
        "--convert-to", "pdf",
        "--outdir", str(output_dir),
        str(docx),
    ]
    if verbose:
        print(f"    libreoffice: {docx.name} → {docx.stem}.pdf")
    if _run(cmd, "libreoffice pdf"):
        out = output_dir / (docx.stem + ".pdf")
        return out if out.exists() else None
    return None


def to_pdf_pandoc(docx: Path, output_dir: Path, verbose: bool) -> Path | None:
    """Fallback: convert docx → PDF via pandoc (requires LaTeX or weasyprint)."""
    out = output_dir / (docx.stem + ".pdf")
    cmd = [
        "pandoc",
        str(docx),
        "--from=docx",
        "--output", str(out),
    ]
    if verbose:
        print(f"    pandoc (pdf fallback): {docx.name} → {out.name}")
    if _run(cmd, "pandoc pdf"):
        return out
    return None


def convert(docx: Path, output_dir: Path, formats: list[str], verbose: bool) -> dict:
    results = {"html": None, "pdf": None}

    if "html" in formats:
        if not _check_tool("pandoc", "macOS: brew install pandoc"):
            pass
        else:
            results["html"] = to_html(docx, output_dir, verbose)

    if "pdf" in formats:
        soffice = shutil.which("soffice") or shutil.which("libreoffice")
        if soffice:
            results["pdf"] = to_pdf_libreoffice(docx, output_dir, verbose)
        else:
            # graceful fallback to pandoc-based PDF
            results["pdf"] = to_pdf_pandoc(docx, output_dir, verbose)

    return results


# ── main ─────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert .docx files to PDF and/or HTML.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "files",
        nargs="*",
        metavar="FILE.docx",
        help="Specific .docx files to convert (default: all .docx in current directory)",
    )
    parser.add_argument(
        "--formats",
        default="pdf,html",
        help="Comma-separated list of output formats: pdf,html (default: pdf,html)",
    )
    parser.add_argument(
        "--output-dir",
        default="converted",
        metavar="DIR",
        help="Directory for converted files (default: ./converted/)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show conversion commands",
    )
    args = parser.parse_args()

    formats = [f.strip().lower() for f in args.formats.split(",") if f.strip()]
    invalid = [f for f in formats if f not in ("pdf", "html")]
    if invalid:
        print(f"ERROR: unsupported format(s): {', '.join(invalid)}. Use pdf and/or html.")
        return 1

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Collect target files
    if args.files:
        docx_files = [Path(f) for f in args.files]
        missing = [f for f in docx_files if not f.exists()]
        if missing:
            print(f"ERROR: file(s) not found: {', '.join(str(f) for f in missing)}")
            return 1
    else:
        docx_files = sorted(Path(".").glob("*.docx"))

    if not docx_files:
        print("No .docx files found.")
        return 0

    print(f"Converting {len(docx_files)} file(s) → {output_dir}/ [{', '.join(formats)}]")
    print()

    ok = 0
    failed = 0

    for docx in docx_files:
        print(f"  {docx.name}")
        results = convert(docx, output_dir, formats, args.verbose)

        file_ok = True
        for fmt in formats:
            out = results.get(fmt)
            if out and out.exists():
                size = out.stat().st_size
                print(f"    ✓ {out.name}  ({size:,} bytes)")
            else:
                print(f"    ✗ {fmt} conversion failed")
                file_ok = False

        if file_ok:
            ok += 1
        else:
            failed += 1
        print()

    print(f"Done: {ok} succeeded, {failed} failed.")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
