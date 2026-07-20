---
name: Change concepts
about: 'To change information of the exsisting concepts from SoilVoc. '
title: "[change-concepts]"
labels: ''
assignees: ''
type: Bug

---

Use this template to propose changes to existing terms, properties, or procedures in SoilVoc, or to add additional definitions or descriptions. If you believe that the definition of an existing concept is incorrect, incomplete, or could benefit from an alternative definition or description, please use this template. 


Before submitting a request, please consult SoilVoc. If you would like to add a new term, property, or procedure, please use the corresponding New Term, New Property, or New Procedure template instead of the Change Terms template. 

### Fields specification

**`id`** *(required)*  
The identifier of the concept from soilvoc.  
*Use a URI.*

**`prefLabel`**  
The preferred label, similar to the one used in SoilVoc.  
*Free text; English preferred.*

**`definition`**  
A clear textual definition of the term, procedure, or property in English. Should describe the concept, not just restate the label.  
*Free text; separate multiple values with semicolons.*

**`broader`**  
Reference to a more general term from soilvoc.  
*Use a soilvoc URI.*

**`exactMatch`**  
Reference to an equivalent concept in an external vocabulary or authoritative source.  
*Use a URI; separate multiple values with semicolons.*

**`closeMatch`**  
Reference to a closely related concept in an external vocabulary or authoritative source.  
*Use a URI; separate multiple values with semicolons.*

**`sourceLink`**  
Link to the authoritative source defining this concept.  
*Use a stable link (URL / URI / DOI, etc.).*

### Contribution workflow

Download the template below, complete it with your content, attach it to this Git issue, and submit the issue.

[template_changeconcepts.csv](https://github.com/soilwise-he/soil-vocabs/blob/main/templates/template_changeconcepts.csv)
