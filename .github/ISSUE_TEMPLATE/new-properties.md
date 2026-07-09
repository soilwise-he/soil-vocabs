---
name: New properties
about: To add new soil properties to SoilVoc.
title: "[new-properties]"
labels: ''
assignees: ''
type: Feature

---

Use this template to add new soil properties to SoilVoc. Before submitting a new property, please consult SoilVoc to ensure that the property does not already exist. This template is intended only for adding properties that are not yet included in SoilVoc. If you would like to propose a different definition for an existing property, please use the “Change Terms” template instead. 


### Fields specification

**`prefLabel`** *(required)*  
The preferred label of the property in English.  
*Free text in English.*

**`definition`** *(required)*  
A clear textual definition of the concept in English. Should describe the meaning of the property, not just restate the label.

**`broaderTerm`** *(required)*  
Reference to a more general term.  
*Use a soilvoc URI; separate multiple values with semicolons.*

**`exactMatch`**  
Reference to an equivalent property in an external vocabulary or authoritative source.  
*Use a URI; separate multiple values with semicolons.*

**`closeMatch`**  
Reference to a closely related property in an external vocabulary or authoritative source.  
*Use a URI; separate multiple values with semicolons.*

**`sourceLink`** *(required)*  
Link to the authoritative source defining this property.  
*Use a stable link (URL / URI / DOI, etc.).*

### Contribution workflow

Download the template below, complete it with your content, attach it to this Git issue, and submit the issue.

[template_addproperty.csv](https://github.com/soilwise-he/soil-vocabs/blob/main/SoilVoc_concepts.csv)
