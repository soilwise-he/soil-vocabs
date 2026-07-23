# SoilVoc comprehensive revision

Date: 2026-07-23

Branch: `codex/soilvoc-comprehensive-expansion`

## Scope

This revision expands SoilVoc from 1,048 to 1,416 concepts. The editable
source remains `SoilVoc_concepts.csv`; `SoilVoc.ttl` and
`assets/soilvoc_data.json` are regenerated artifacts. The viewer data version
is now `v0.2.0`.

The revision adds 368 concepts covering soil entities and profiles,
classification, biology, nutrients and carbon, processes, materials, soil
types, contaminants, threats, management, restoration, soil health and
quality, functions and ecosystem services, and investigation and monitoring.

## Modeling invariants

- Every concept is identified by a local URI under
  `https://w3id.org/eusoilvoc#`.
- Every concept belongs to the single concept scheme
  `https://w3id.org/eusoilvoc`.
- External concepts occur only as `skos:exactMatch` or `skos:closeMatch`
  objects. External URIs are never used as SoilVoc concept subjects.
- No definitions were added to the 368 new concepts. Existing definitions
  were retained.
- Observable properties and procedures remain connected only through
  `sosa:hasProcedure` and `sosa:isProcedureFor`.
- No `skos:broader` relation was added between an observable property and a
  procedure.
- The pre-existing 860 `sosa:hasProcedure` and 860
  `sosa:isProcedureFor` assertions are unchanged. The vocabulary still has
  249 procedure concepts and 57 observable-property concepts.

`skos:exactMatch` is used when the source concept and local concept have the
same intended meaning. `skos:closeMatch` is used when the relationship is
useful but classification system, scope, grammatical form, or source
modeling makes identity too strong.

## Added coverage

### Soil entities, profiles, and morphology

Added soil profile, pedon and polypedon, soil body, profile elements, soil
horizon and layer, topsoil and subsoil, solum, regolith, saprolite,
rhizosphere, bulk soil, map units and series, master horizons, soil
morphology, Munsell color, structural types, roots, redoximorphic features,
and restrictive layers.

### Soil classification

Added local branches for WRB and USDA Soil Taxonomy inside the existing
SoilVoc scheme. The WRB branch contains all 32 Reference Soil Groups from the
WRB fourth edition, corrected in 2024, using the
[official WRB inventory](https://wrb.isric.org/soilgroups/) and
[corrected edition](https://wrb.isric.org/files/WRB_fourth_edition_2022-12-18_errata_correction_2024-09-24.pdf).
The USDA branch contains all 12 soil orders from the
[official USDA inventory](https://www.nrcs.usda.gov/resources/education-and-teaching-materials/the-twelve-orders-of-soil-taxonomy).
Qualified preferred labels such as `WRB Histosol` and
`USDA Histosol` avoid collisions while preserving the unqualified names as
alternative labels. WRB diagnostic horizons, properties, and materials were
also added as organizing concepts.

This revision deliberately does not create separate WRB or USDA concept
schemes.

### Soil biology

Added major microbial groups, fungi and mycorrhizae, soil fauna size groups,
biological diversity and activity, microbial biomass carbon, nitrogen and
phosphorus, bacterial and fungal biomass, enzyme activities, substrate-induced
respiration, food webs, necromass, and root distribution and depth.

### Nutrients and carbon

Added mineral and organic nitrogen forms, nitrate, nitrite and ammonium,
phosphorus forms, sulfate and chloride, dissolved and particulate organic
matter, mineral-associated organic matter, labile carbon, soil organic carbon
stock, elemental ratios, nutrient status, and nutrient availability.

### Processes

Added pedogenic, biological, chemical, physical, and degradative processes,
including weathering, decomposition, humification, nitrification,
ammonification, eluviation, illuviation, lessivage, podzolization, gleying,
calcification, decalcification, salinization, sodification, nutrient cycling,
carbon sequestration, and peat oxidation.

### Materials, minerals, and soil types

Added soil materials and amendments, mineral and organic soils, acid sulfate
soil, peat soil, volcanic soil, anthropogenic soil, common clay and primary
mineral species, and mineral and organic amendment materials. Amendment
materials are modeled separately from amendment application practices.

### Contaminants and threats

Added potentially toxic elements, hydrocarbons, PAHs, PCBs, PFAS, petroleum
hydrocarbons, pesticide residues, antibiotics, radionuclides, microplastics,
pathogens, antimicrobial-resistance genes, and contaminant fractions. Threat
coverage now includes erosion subtypes, waterlogging, flooding, landslides,
alkalization, drought, wildfire, pollution subtypes, and contaminated sites.

### Management, restoration, and remediation

Added crop rotation, cover cropping, intercropping, reduced and no tillage,
controlled traffic, residue management, fertilizer and amendment application,
conservation practices, restoration, rehabilitation, regeneration,
remediation, risk-reduction measures, and representative remediation methods.

### Soil health, quality, functions, and services

Added soil condition, health and quality assessments, indicator categories,
baselines, thresholds, critical limits, targets and scores, resilience,
resistance, recovery, and fertility. Function and ecosystem-service additions
include biomass production, erosion control, flood mitigation, contaminant
attenuation, biodiversity support, archaeological preservation, and water
conservation.

### Investigation and monitoring

Added the top concept `soil investigation and monitoring`, with soil survey,
investigation, monitoring, sampling, samples, sample preparation, field and
laboratory measurement, quality assurance, quality control, descriptors,
districts, and units beneath it.

## Alignment sources

Mappings for added concepts were selected from the source snapshots stored in
`ontovocabs/` and from the referenced classification standards. A total of 223
new concepts have at least one external mapping. They carry 359
`skos:exactMatch` and 71 `skos:closeMatch` assertions:

| Source | Mapping assertions on added concepts |
| --- | ---: |
| AGROVOC | 168 |
| INRAE Thesaurus | 99 |
| Soil Health Knowledge Graph | 93 |
| GEMET | 43 |
| ISO 11074:2025 vocabulary snapshot | 23 |
| GloSIS 1.5.1 | 4 |

The official WRB soil-group inventory and USDA soil-order inventory were used
to complete the two classification branches. Their classifications are
represented with local SoilVoc URIs. No unstable page or document fragment
was asserted as a SKOS mapping solely to provide a link.

Several concepts from the repository's Soil Monitoring Law snapshot reuse the
already proposed local SoilVoc identifiers, including managed soil, mineral
soil, organic soil, net sealing, sealed soil, soil descriptor, soil district,
soil unit, soil management practice, risk, and risk-reduction measure. These
local concepts do not map to themselves.

Mappings are editorial assertions, not imports. They should receive domain
review before a formal release, especially mappings across classification
systems and mappings currently marked `skos:closeMatch`. Source licenses were
not used as an exclusion criterion for URI mappings in this revision; that
does not constitute a licensing review or clearance for later content reuse.

## Repairs to existing concepts

Stable local URIs were retained while these preferred labels were corrected:

- `evapouration` to `evaporation`
- `soil water evapouration` to `soil water evaporation`
- `geometric mean diametre` to `geometric mean diameter`
- `peat decompostion` to `peat decomposition`
- `groundwater reproduction` to `groundwater recharge`

The former labels remain alternative labels. Existing narrower references
were updated by label resolution during regeneration.

The groundwater-recharge SHKG alignment was changed from the misleading
`GroundwaterReproduction` target to `GroundwaterRecharge`; the former target
is retained only as a close mapping. Targeted mappings and broader relations
were also added or tightened for microbial biomass, denitrification,
desertification, hydraulic conductivity, drainage, subsidence, salinization,
and sulfur. A duplicate local soil-sodification concept was avoided by using
the single local `Sodification` concept.

## Regeneration and validation

Regenerate the RDF and viewer payload from the repository root:

```powershell
python scripts/restore_soilvoc_from_csv.py --csv SoilVoc_concepts.csv --out SoilVoc_restored.ttl --compare SoilVoc.ttl
python scripts/generate_soilvoc_html.py
```

The revision was checked for local concept URIs, one concept scheme, resolvable
broader labels, duplicate identifiers and preferred labels, broader cycles,
mapping-predicate conflicts, classification counts, and preservation of the
SOSA procedure model. `git diff --check` and generated-artifact comparisons
were also run.
