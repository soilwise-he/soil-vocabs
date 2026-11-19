"""Check labels attached to a [check-duplicate] issue against SoilVoc.

Reads the issue body (the text after the title), finds the single CSV/XLSX
attachment, reads its ``label`` or ``prefLabel`` column and looks for existing
SoilVoc concepts that each label may duplicate. The result is written as a
Markdown issue comment to ``--comment-file``; the workflow posts it.

Matching, per input label (first hit wins):
  1. Exact label  -> label equals a SoilVoc prefLabel or altLabel
                     (case-insensitive, whitespace-normalised). Score 1.
  2. Retrieve + rerank, ported from metadata-augmentation/keyword-matcher/match.py:
       a. bi-encoder top-k nearest SoilVoc labels (prefLabels + altLabels,
          cosine >= COSINE_FLOOR), deduplicated to the best label per concept;
       b. cross-encoder scores (input label, "prefLabel: definition");
       c. the best candidate is reported if its score >= CE_THRESHOLD.

Exit codes: 0 whenever a comment was produced, including for user-facing
problems such as a missing attachment. Non-zero only for internal errors; a
comment describing the failure is still written so the issue gets an answer.
"""

import argparse
import csv
import io
import logging
import math
import re
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path

COMMENT_MARKER = "<!-- check-duplicates -->"

SUPPORTED_EXTENSIONS = (".csv", ".xlsx")
LABEL_COLUMNS = ("preflabel", "label")  # preference order, compared case-insensitively
MAX_ROWS = 500
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024

BI_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
CE_MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"
TOP_K = 15            # nearest SoilVoc labels retrieved per input label
COSINE_FLOOR = 0.40   # drop retrieved candidates below this before reranking
CE_THRESHOLD = 0.60   # 0-1 sigmoid score; placeholder, recalibrate on a gold set
CE_MAX_LENGTH = 128

URL_RE = re.compile(r"https?://[^\s)\]}<>\"']+")
ATTACHMENT_RE = re.compile(
    r"^https?://(?:www\.)?github\.com/(?:user-attachments/files/\d+/|[^/]+/[^/]+/files/\d+/)",
    re.IGNORECASE,
)


class CheckError(Exception):
    """A problem with the submission, reported to the contributor as-is."""


@dataclass
class Concept:
    uri: str
    pref_label: str
    alt_labels: list[str]
    definition: str | None

    @property
    def enriched_text(self) -> str:
        return f"{self.pref_label}: {self.definition}" if self.definition else self.pref_label


@dataclass
class InputLabel:
    row: int     # row number as shown in a spreadsheet (header = row 1)
    label: str


@dataclass
class Match:
    item: InputLabel
    concept: Concept
    score: float


def norm_label(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip().casefold()


# --------------------------------------------------------------------------- attachment

def find_attachments(text: str) -> list[str]:
    """GitHub attachment URLs in the text, in order of appearance, deduplicated."""
    urls: list[str] = []
    for raw in URL_RE.findall(text or ""):
        url = raw.rstrip(".,;:")
        if ATTACHMENT_RE.match(url) and url not in urls:
            urls.append(url)
    return urls


def attachment_name(url: str) -> str:
    return Path(urllib.parse.unquote(urllib.parse.urlparse(url).path)).name or "attachment"


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "soil-vocabs-ci"})
    try:
        with urllib.request.urlopen(request, timeout=60) as response:
            data = response.read(MAX_DOWNLOAD_BYTES + 1)
    except urllib.error.URLError as exc:
        raise CheckError(f"The attachment `{attachment_name(url)}` could not be downloaded ({exc}).")
    if len(data) > MAX_DOWNLOAD_BYTES:
        raise CheckError(
            f"The attachment `{attachment_name(url)}` is larger than "
            f"{MAX_DOWNLOAD_BYTES // (1024 * 1024)} MB."
        )
    return data


# --------------------------------------------------------------------------- reading

def read_csv_rows(data: bytes) -> list[list[str]]:
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise CheckError("The CSV file is not UTF-8 encoded. Please save it as \"CSV UTF-8\".")
    first_line = text.split("\n", 1)[0]
    try:
        dialect = csv.Sniffer().sniff(first_line, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    try:
        return [row for row in csv.reader(io.StringIO(text), dialect)]
    except csv.Error as exc:
        raise CheckError(f"The CSV file could not be parsed ({exc}).")


def read_xlsx_rows(data: bytes) -> list[list[str]]:
    from openpyxl import load_workbook

    try:
        workbook = load_workbook(io.BytesIO(data), read_only=True, data_only=True)
    except Exception as exc:  # openpyxl raises several unrelated types for bad files
        raise CheckError(f"The Excel file could not be opened ({type(exc).__name__}: {exc}).")
    try:
        if not workbook.worksheets:
            raise CheckError("The Excel file contains no worksheets.")
        sheet = workbook.worksheets[0]
        return [
            ["" if cell is None else str(cell) for cell in row]
            for row in sheet.iter_rows(values_only=True)
        ]
    finally:
        workbook.close()


def extract_labels(rows: list[list[str]]) -> tuple[list[InputLabel], str]:
    """Return the non-empty labels and the name of the column they came from."""
    if not rows:
        raise CheckError("The file is empty.")
    header = [norm_label(h) for h in rows[0]]
    column = None
    for wanted in LABEL_COLUMNS:
        if wanted in header:
            column = header.index(wanted)
            break
    if column is None:
        found = ", ".join(f"`{h.strip()}`" for h in rows[0] if h.strip()) or "none"
        raise CheckError(
            "The file has no `label` or `prefLabel` column in its first row "
            f"(columns found: {found})."
        )

    items = []
    for offset, row in enumerate(rows[1:], start=2):
        value = row[column].strip() if column < len(row) else ""
        if value:
            items.append(InputLabel(row=offset, label=re.sub(r"\s+", " ", value)))

    if not items:
        raise CheckError(f"The `{rows[0][column].strip()}` column contains no labels.")
    if len(items) > MAX_ROWS:
        raise CheckError(
            f"The file contains {len(items)} labels; at most {MAX_ROWS} can be checked at once. "
            "Please split it over several issues."
        )
    return items, rows[0][column].strip()


# --------------------------------------------------------------------------- vocabulary

def load_concepts(ttl_path: Path) -> list[Concept]:
    from rdflib import Graph, Literal
    from rdflib.namespace import RDF, SKOS

    graph = Graph()
    graph.parse(ttl_path, format="turtle")

    def english_first(literals):
        literals = [lit for lit in literals if isinstance(lit, Literal)]
        literals.sort(key=lambda lit: (lit.language not in (None, "en"), str(lit)))
        return [str(lit) for lit in literals]

    concepts = []
    for uri in sorted(set(graph.subjects(RDF.type, SKOS.Concept)), key=str):
        prefs = english_first(graph.objects(uri, SKOS.prefLabel))
        if not prefs:
            continue
        definitions = []
        for node in graph.objects(uri, SKOS.definition):
            if isinstance(node, Literal):
                definitions.append(node)
            else:
                definitions.extend(graph.objects(node, RDF.value))
        definitions = english_first(definitions)
        concepts.append(Concept(
            uri=str(uri),
            pref_label=prefs[0],
            alt_labels=english_first(graph.objects(uri, SKOS.altLabel)),
            definition=definitions[0] if definitions else None,
        ))
    return concepts


# --------------------------------------------------------------------------- matching

def exact_matches(items: list[InputLabel], concepts: list[Concept]):
    """Return (matches, unmatched items). prefLabels take precedence over altLabels."""
    index: dict[str, Concept] = {}
    for concept in concepts:
        index.setdefault(norm_label(concept.pref_label), concept)
    for concept in concepts:
        for alt in concept.alt_labels:
            index.setdefault(norm_label(alt), concept)

    matches, rest = [], []
    for item in items:
        concept = index.get(norm_label(item.label))
        if concept is not None:
            matches.append(Match(item, concept, 1.0))
        else:
            rest.append(item)
    return matches, rest


def semantic_matches(items: list[InputLabel], concepts: list[Concept]) -> list[Match]:
    if not items:
        return []

    import torch
    from sentence_transformers import CrossEncoder, SentenceTransformer, util

    corpus_labels, corpus_concept = [], []
    for ci, concept in enumerate(concepts):
        for label in [concept.pref_label, *concept.alt_labels]:
            corpus_labels.append(label)
            corpus_concept.append(ci)

    logging.info("Embedding %d SoilVoc labels and %d input labels", len(corpus_labels), len(items))
    bi_model = SentenceTransformer(BI_MODEL_NAME)
    corpus_emb = bi_model.encode(corpus_labels, convert_to_tensor=True,
                                 normalize_embeddings=True, show_progress_bar=False)
    query_emb = bi_model.encode([i.label for i in items], convert_to_tensor=True,
                                normalize_embeddings=True, show_progress_bar=False)
    hits = util.semantic_search(query_emb, corpus_emb, top_k=TOP_K, score_function=util.cos_sim)

    pairs, meta = [], []  # (input label, enriched text), (item index, concept index)
    for qi, item_hits in enumerate(hits):
        best: dict[int, float] = {}
        for hit in item_hits:
            if hit["score"] < COSINE_FLOOR:
                continue
            ci = corpus_concept[hit["corpus_id"]]
            best[ci] = max(best.get(ci, -1.0), hit["score"])
        for ci in best:
            pairs.append((items[qi].label, concepts[ci].enriched_text))
            meta.append((qi, ci))

    logging.info("Cross-encoder pairs to score: %d", len(pairs))
    if not pairs:
        return []

    ce_model = CrossEncoder(CE_MODEL_NAME, activation_fn=torch.nn.Sigmoid(), max_length=CE_MAX_LENGTH)
    scores = ce_model.predict(pairs, show_progress_bar=False)

    best_by_item: dict[int, tuple[float, int]] = {}
    for (qi, ci), score in zip(meta, scores):
        score = float(score)
        if qi not in best_by_item or score > best_by_item[qi][0]:
            best_by_item[qi] = (score, ci)

    # Truncate to two decimals and cap at 0.99 so that a reported 1.00 always
    # means an exact label match (CE sigmoid scores can reach 0.9996).
    return [
        Match(items[qi], concepts[ci], min(math.floor(score * 100) / 100, 0.99))
        for qi, (score, ci) in best_by_item.items()
        if score >= CE_THRESHOLD
    ]


def repeated_labels(items: list[InputLabel]) -> list[list[InputLabel]]:
    groups: dict[str, list[InputLabel]] = {}
    for item in items:
        groups.setdefault(norm_label(item.label), []).append(item)
    return [group for group in groups.values() if len(group) > 1]


# --------------------------------------------------------------------------- reporting

def cell(value: str) -> str:
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ")


def report(file_name: str, column: str, items, matches, repeats) -> str:
    lines = [
        COMMENT_MARKER,
        "## SoilVoc duplicate check",
        "",
        f"Checked {len(items)} label(s) from the `{cell(column)}` column of `{cell(file_name)}`.",
        "",
    ]
    if matches:
        lines += [
            f"### Possible duplicates ({len(matches)} of {len(items)} labels)",
            "",
            "| Row | Input label | SoilVoc prefLabel | SoilVoc URI | Match score |",
            "|---:|---|---|---|---:|",
        ]
        for m in sorted(matches, key=lambda m: m.item.row):
            lines.append(
                f"| {m.item.row} | {cell(m.item.label)} | {cell(m.concept.pref_label)} "
                f"| {m.concept.uri} | {m.score:.2f} |"
            )
        lines += [
            "",
            "A score of 1.00 means the label is already a SoilVoc prefLabel or altLabel. "
            f"Lower scores are semantic similarity (shown when ≥ {CE_THRESHOLD:.2f}); "
            "please review them before proposing the term.",
            "",
        ]
    else:
        lines += ["No existing SoilVoc concepts match the submitted labels.", ""]

    if repeats:
        lines += ["### Warnings", ""]
        for group in repeats:
            rows = ", ".join(str(i.row) for i in group)
            lines.append(f"- ⚠️ `{cell(group[0].label)}` appears more than once in the file (rows {rows}).")
        lines.append("")

    lines += ["<sub>Row numbers count the header as row 1. "
              "Edit the issue or comment `/check-duplicates` to run the check again.</sub>"]
    return "\n".join(lines) + "\n"


def error_report(message: str, hint: bool = True) -> str:
    lines = [COMMENT_MARKER, "## SoilVoc duplicate check", "", f"❌ **The check could not run:** {message}", ""]
    if hint:
        lines += [
            "Please attach exactly one `.csv` or `.xlsx` file with a `label` or `prefLabel` column "
            "to the issue description, then edit the issue or comment `/check-duplicates`.",
            "",
        ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- main

def run(issue_body: str, ttl_path: Path) -> str:
    urls = find_attachments(issue_body)
    if not urls:
        raise CheckError("No file is attached to the issue description.")
    if len(urls) > 1:
        names = ", ".join(f"`{cell(attachment_name(u))}`" for u in urls)
        raise CheckError(f"{len(urls)} files are attached ({names}); please attach exactly one.")

    url = urls[0]
    name = attachment_name(url)
    suffix = Path(name).suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise CheckError(
            f"`{cell(name)}` is not a supported file type. Supported: "
            + ", ".join(f"`{s}`" for s in SUPPORTED_EXTENSIONS) + "."
        )

    logging.info("Downloading %s", url)
    data = download(url)
    rows = read_csv_rows(data) if suffix == ".csv" else read_xlsx_rows(data)
    items, column = extract_labels(rows)
    logging.info("Read %d label(s) from column %r", len(items), column)

    concepts = load_concepts(ttl_path)
    logging.info("Loaded %d SoilVoc concepts", len(concepts))

    matches, rest = exact_matches(items, concepts)
    logging.info("Exact matches: %d; sent to retrieve + rerank: %d", len(matches), len(rest))
    matches += semantic_matches(rest, concepts)

    return report(name, column, items, matches, repeated_labels(items))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--body-file", type=Path, required=True, help="File holding the issue description")
    parser.add_argument("--ttl", type=Path, default=Path("SoilVoc.ttl"))
    parser.add_argument("--comment-file", type=Path, required=True, help="Where to write the Markdown comment")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(message)s")

    status = 0
    try:
        comment = run(args.body_file.read_text(encoding="utf-8"), args.ttl)
    except CheckError as exc:
        logging.info("Submission problem: %s", exc)
        comment = error_report(str(exc))
    except Exception:
        traceback.print_exc()
        comment = error_report(
            "an internal error occurred while processing the file. "
            "A maintainer needs to look at the failed workflow run.",
            hint=False,
        )
        status = 1

    args.comment_file.write_text(comment, encoding="utf-8")
    print(comment)
    return status


if __name__ == "__main__":
    raise SystemExit(main())
