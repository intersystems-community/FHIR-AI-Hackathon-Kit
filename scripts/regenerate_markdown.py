"""Regenerate the markdown version of every tutorial notebook.

Each Tutorials/**/X.ipynb is converted to markdown/X.md in the notebook's own
folder (overwriting any existing file), with output images written to
markdown/X_files/, matching `jupyter nbconvert --to markdown`. Notebooks are converted as saved; they are
not re-executed, so outputs reflect the last run.

Usage:
    python scripts/regenerate_markdown.py
"""

import time
from pathlib import Path

import nbformat
from nbconvert import MarkdownExporter
from nbconvert.writers import FilesWriter

TUTORIAL_ROOT = Path(__file__).resolve().parent.parent / "Tutorials"


def main():
    notebooks = sorted(
        p for p in TUTORIAL_ROOT.rglob("*.ipynb") if ".ipynb_checkpoints" not in p.parts
    )
    if not notebooks:
        raise FileNotFoundError(f"No notebooks found under {TUTORIAL_ROOT}")

    exporter = MarkdownExporter()
    start = time.perf_counter()
    for i, nb_path in enumerate(notebooks, 1):
        print(f"[{i}/{len(notebooks)}] {nb_path.relative_to(TUTORIAL_ROOT)}", flush=True)
        nb = nbformat.read(nb_path, as_version=4)
        body, resources = exporter.from_notebook_node(
            nb,
            resources={"output_files_dir": f"{nb_path.stem}_files"},
        )
        writer = FilesWriter(build_directory=str(nb_path.parent / "markdown"))
        out = writer.write(body, resources, notebook_name=nb_path.stem)
        n_images = len(resources.get("outputs", {}))  # absent when notebook has no image outputs
        print(f"    -> {Path(out).relative_to(TUTORIAL_ROOT)} ({n_images} image(s))", flush=True)

    print(f"Done: {len(notebooks)} notebook(s) in {time.perf_counter() - start:.1f}s")


if __name__ == "__main__":
    main()
