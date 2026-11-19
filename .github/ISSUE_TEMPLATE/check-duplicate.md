---
name: Check duplicates
about: Check whether a list of terms already exists in SoilVoc before proposing them
title: "[check-duplicate]"
labels: ''
assignees: ''

---

Use this template to check whether terms you want to propose already exist in SoilVoc. This is a pre-check only: it does not add anything to SoilVoc. 

### How to check your list

- Attach one csv or xlsx file to this issue description. 

- The file must contain a column named `label` or `prefLabel` (case-insensitive).

- One term per row. At most 500 terms.

### What happens next

A bot reads the file and posts a comment listing terms that may already exist in SoilVoc, with the matching SoilVoc concept and a match score:

- 1.00: the term is already a SoilVoc prefLabel or altLabel.
- below 1.00: the term is semantically similar to an existing concept. 

