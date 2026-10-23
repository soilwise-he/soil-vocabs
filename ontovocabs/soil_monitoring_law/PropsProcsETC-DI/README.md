## Observable Properties and Observing Procedures from SML

Assumes 2 Concept Schemes:
- SMLDescriptors
- SMLMethods

Sheets:
- Top Concept: `Aspect of soil degradation` from SML Annex 1. Provided as a grouping mechanism for the actual soil descriptors (Observable Properties)
- Properties Valid: Soil descriptors and indicators from SML Annex 1, Parts A-D
  - skos:broader: links to `Aspect of soil degradation` from Top Concept list. Note that these concepts can span multiple Parts
  - skos:scopeNote: Indication if concept is Mandatory, Optional or Conditional in SML context
  - qudt:applicableUnit: specific UoM from SML. Not using QuantityKind here as SML is specific.
  - skos:historyNote: Full descriptive text from SML. Provided for all concepts, but especially relevant on those that had to be disaggregated to form clean Observable Properties, e.g.
    - `concentration of heavy metals in soil: As, Sb, Cd, Co, Cr (total), Cu, Hg, Pb, Ni, Tl, V, Zn (mg per kg)`
    - `Soil sealing and soil removal, de-sealing and net-sealing (average per year – in km2 and % of Member State surface)`
- Methods: Observing Procedures
  - sosa:forProperty: link to Property skos:notation
- Collections: as the `Aspect of soil degradation` can go across multiple Annex Parts, a skos:Collection has been created for each Annex Part, members are all Observable Properties from that Part

 
