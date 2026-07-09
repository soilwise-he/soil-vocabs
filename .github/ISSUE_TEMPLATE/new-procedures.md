---
name: New procedures
about: To add new soil procedures to SoilVoc.
title: "[new-procedures]"
labels: ''
assignees: ''
type: Feature

---

Use this template to add new procedures to SoilVoc. The procedure must relate to a soil property that is already documented in SoilVoc. Before submitting a new procedure, please consult SoilVoc to ensure that the procedure does not already exist. This template is intended only for adding procedures that are not yet included in SoilVoc. 

If you would like to propose a different definition for an existing procedure, please use the “Change Terms” template instead. If the soil property measured by the procedure is not yet included in SoilVoc, please first add the property using the “New Property” template.


### Fields specification

**`prefLabel`** *(required)*  
The preferred label of the procedure in the given language.  
*Free text; English preferred.*

**`definition`** *(required)*  
A clear textual definition of the procedure in English. Should describe the procedure, not just restate the label.

**`property`** *(required)*  
Go to soilvoc and find the URI of the property your procedure falls under.  
*Use a soilvoc URI. If your property is not yet applied, use the prefLabel defined by you instead.*

**`exactMatch`**  
Reference to an equivalent concept in an external vocabulary or authoritative source.  
*Use a URI; separate multiple values with semicolons.*

**`closeMatch`**  
Reference to a closely related concept in an external vocabulary or authoritative source.  
*Use a URI; separate multiple values with semicolons.*

**`sourceLink`** *(required)*  
Link to the authoritative source defining this procedure.  
*Use a stable link (URL / URI / DOI, etc.).*

### Contribution workflow

Download the template below, complete it with your content, attach it to this Git issue, and submit the issue.

[template_addprocedure.csv](https://github.com/soilwise-he/soil-vocabs/blob/main/SoilVoc_concepts.csv)
