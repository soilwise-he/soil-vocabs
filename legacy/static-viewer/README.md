# Archived Static Viewer

This folder preserves the former hand-written HTML/JavaScript SoilVoc viewer.
The published site now builds from `viewer/`; none of these files are included
in the GitHub Pages artifact.

- `index.html` and `assets/`: the previous page, styles, scripts, images, and JSON snapshot.
- `scripts/generate_soilvoc_html.py`: its former JSON/HTML generation tooling.
- `workflows/update-viewer-data-from-csv.yml`: the old combined workflow, retained
  as a reference only. Its container-publishing role now lives in
  `.github/workflows/build-api-image.yml`.

To inspect the archived viewer, serve the repository root with
`python -m http.server` and open `http://localhost:8000/legacy/static-viewer/`.
Its optional generator can be run from the repository root with
`python legacy/static-viewer/scripts/generate_soilvoc_html.py`; it writes only
the archived JSON snapshot, not the new viewer.
