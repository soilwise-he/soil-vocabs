---
name: Add terms
about: To add new terms (non-property, non-procedure) to SoilVoc
title: "[add-terms]"
labels: ''
assignees: ''
type: Feature

---

Use this template to add new terms to SoilVoc. Before submitting a new term, please consult SoilVoc to ensure that the term does not already exist. This template is intended only for adding terms that are not yet included in SoilVoc. If you would like to propose a different definition for an existing term, please use the “Change Concept” template instead. 


### Fields specification

**`prefLabel`** *(required)*  
The preferred label of the term in English.  
*Free text in English.*

**`definition`** *(required)*  
A clear textual definition of the concept. Should describe the meaning of the concept, not just restate the label.  
*Free text in English.*

**`broader`** *(required)*  
Reference to a more general concept from soilvoc.  
*Use a soilvoc URI; separate multiple values with semicolons.*

**`exactMatch`**  
Reference to an equivalent concept in an external vocabulary or authoritative source.  
*Use a URI; separate multiple values with semicolons.*

**`closeMatch`**  
Reference to a closely related concept in an external vocabulary or authoritative source.  
*Use a URI; separate multiple values with semicolons.*

**`sourceLink`** *(required)*  
Link to the authoritative source defining this concept.  
*Use a stable link (URL / URI / DOI, etc.).*

**`publishingOrganisation`**  
Organisation responsible for the definition.  
*Use a consistent organisation name; avoid free-text variation where possible; use the English name of the organisation.*

**`titleOrReferenceToDocument`**  
Title or reference of the source document.  
*Use the official title as published by the source.*

### Contribution workflow

Download the template below, complete it with your content, attach it to this Git issue, and submit the issue.

[template_addterms.csv](https://github.com/soilwise-he/soil-vocabs/blob/main/templates/template_addterms.csv)
