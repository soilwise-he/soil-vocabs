---
name: Check duplicates
about: Check whether a list of terms already exists in SoilVoc before proposing them
title: "[check-duplicate]"
labels: ''
assignees: ''

---

Use this template to check whether terms you want to propose already exist in SoilVoc. This is a pre-check only: it does not add anything to SoilVoc. To propose new terms afterwards, use the "Add terms", "Add properties" or "Add procedures" template.

### What to attach

Attach **exactly one** file to this issue description (drag and drop it into this text box):

- **File type:** `.csv` (UTF-8 encoded) or `.xlsx`. For `.xlsx` files only the first sheet is read.
- **Column:** the first row must be a header containing a column named `label` or `prefLabel` (case-insensitive). Other columns are ignored.
- **Rows:** one term per row, in English. Empty cells are skipped. At most 500 terms per file.

### What happens next

A bot reads the file and posts a comment listing every term that may already exist in SoilVoc, with the matching SoilVoc concept and a match score:

- **1.00** — the term is already a SoilVoc preferred or alternative label (ignoring case).
- **below 1.00** — the term is semantically similar to an existing concept. Please review these before proposing the term.

Terms with no likely match are not listed. To run the check again after changing the attachment, edit this issue or comment `/check-duplicates`.
