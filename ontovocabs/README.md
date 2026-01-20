# Repository of existing soil vocabularies

A concise **summary and background** for soil/environment/agronomy-related ontologies/vocabularies in this repository

## [ISO 11074](https://www.iso.org/standard/83168.html) – Soil Quality Vocabulary

**What it is:**
An **international standard** defining a harmonized vocabulary of terms used in soil quality and related fields (e.g., soil description, sampling, assessment, remediation). It isn’t an ontology per se, but the terms standardized here are often used as **reference concepts** in semantic models and knowledge graphs. ([ISO][1])

**Background & Creator:**
Published by **ISO (International Organization for Standardization), Technical Committee ISO/TC 190** (Soil quality). The third edition was published in **2025** (ISO 11074:2025). ([ISO][1])

**Use:**
Standardizes terminology across research, policy, regulation, and data systems to ensure consistent interpretation of soil quality terms worldwide — useful in ontology alignment and controlled vocabularies.

**Notes:**
This replaces earlier versions (e.g., 2015) and supports interoperability across soil and environmental semantic resources. ([ISO][1])

## Soil health Monitoring law

**What it is:**
Defines key terms and concepts related to soil health monitoring, assessment, and management within the context of EU legislation. While not a formal ontology, it provides **standardized definitions** that can be referenced in semantic models related to soil health. 

**Background & Creator:**
EU

## INRAE Thesaurus

**What it is:**
A **large controlled vocabulary (thesaurus)** covering agriculture, environment, food and related research areas maintained by INRAE (Institut National de Recherche pour l’Agriculture, l’Alimentation et l’Environnement). It’s published in SKOS/OWL formats and functions like a broad semantic reference. [thesaurus.inrae.fr](https://thesaurus.inrae.fr)

**Background & Creator:**
Developed and maintained by **INRAE**, first published in 2021. Contains **>16 000 concepts** relevant to agronomy, environment, earth sciences, etc. ([agroportal.lirmm.fr][3])

**Use:**
Serves for annotating datasets, documents, and research outputs, and is often **aligned with AGROVOC, GEMET, and other vocabularies** to enable broader semantic integration. ([vocabulaires-ouverts.inrae.fr][4])



## GEMET – GEneral Multilingual Environmental Thesaurus

**What it is:**
A **multilingual environmental thesaurus** providing a core set of general environmental terminology in many European languages. It’s often used as a backbone in semantic metadata systems and environmental data catalogs. ([Eionet Portal][5])

**Background & Creator:**
Developed since **1995** under contract for the **European Environment Agency (EEA)** and others in the European environmental information network (EIONET). ([Eionet Portal](https://www.eionet.europa.eu/gemet/en/about))

**Use:**
Provides **general environmental concepts** (soil, water, pollution, etc.) that can be linked or mapped to domain-specific vocabularies like AGROVOC or INRAE Thesaurus, facilitating interdisciplinary interoperability. 



## AGROVOC

**What it is:**
A **comprehensive multilingual agricultural vocabulary** covering agriculture, forestry, fisheries, and related domains. It’s published as **Linked Open Data** (LOD) and connects to many external vocabularies. ([FAOHome](https://www.fao.org/agrovoc/linked-data))

**Background & Creator:**
Maintained by **FAO (Food and Agriculture Organization of the UN)**. Publicly accessible with RDF/SKOS structure and aligned with over a dozen other vocabularies, including GEMET and INRAE Thesaurus. ([FAOHome](https://www.fao.org/agrovoc/linked-data))

**Use:**
Used for indexing, annotating, and integrating agricultural and environmental data globally, and often functions as a **hub vocabulary** in agronomy and environmental knowledge graphs.



## GloSIS-LD – Global Soil Information System Linked Data

**What it is:**
A **soil information ontology/web ontology** developed for harmonizing and representing global soil data semantics, building on soil survey and information standards. ([arXiv](https://arxiv.org/abs/2403.16778))

**Background & Creator:**
Originated within the **Global Soil Partnership (FAO)** to unify soil data semantics across countries and systems, implemented in OWL with support for standards like SOSA, GeoSPARQL, etc. ([arXiv](https://arxiv.org/abs/2403.16778))

**Use:**
Provides a **semantic model for soil description and analysis**, enabling Linked Data publication and integration of heterogeneous soil data internationally.



## Soil Health Benchmarks Glossary

**What it is:**
A **domain-specific glossary** developed by the **Soil Health BENCHMARKS project** (Horizon Europe) to collect terminologies around soil health, soil functions, ecosystem services, and soil indicators. ([Benchmarks](https://soilhealthbenchmarks.eu/glossary))

**Background & Creator:**
Created by EU research partners, this glossary aggregates and clarifies scientific definitions relevant to soil health monitoring and benchmarking. ([Benchmarks][9])

**Use:**
While primarily a glossary rather than a formal ontology, it’s **domain-focused on soil health** and can be used as semantic support for project data and knowledge graphs.



## [IMASH]( https://archive.researchdata.leeds.ac.uk/42) (Soil Properties and Processes Ontology)

> **Note:** There isn’t a widely recognized ontology literally named “Leeds-IMASH” published as a mainstream ontology registry entry; however…

**What exists:**
The **Ontology of Soil Properties and Processes** developed at **University of Leeds** describes soil physical/chemical properties and their interrelationships in OWL. ([archive.researchdata.leeds.ac.uk][10])

**Background & Creator:**
Created by researchers **Heshan Du & Anthony G. Cohn** (University of Leeds) for representing soil properties and processes, using foundational ontologies like NASA’s SWEET and expert/domain knowledge. ([archive.researchdata.leeds.ac.uk]( https://archive.researchdata.leeds.ac.uk/42))

**Use:**
Useful for engineering, environmental modeling, and semantic reasoning about soil physical processes.

---

## Other thesauri/ontologies which could be of interest

Depending on what you’re aiming to cover (integration, semantics, analytics), the following are also widely used in soil/environment/agronomy spaces:

## [SWEET](https://bioportal.bioontology.org/ontologies/SWEET) (Semantic Web for Earth and Environmental Terminology)

A foundational environmental ontology developed under NASA that provides high-level classes for earth sciences and is often reused by domain ontologies (e.g., soil, water, atmosphere).

## [iAdopt](https://i-adopt.github.io/)


## INSPIRE registry

The INSPIRE infrastructure involves a number of items, which require clear descriptions and the possibility to be referenced through unique identifiers. Examples for such items include INSPIRE themes, code lists, application schemas or discovery services. Registers provide a means to assign identifiers to items and their labels, definitions and descriptions (in different languages). The [INSPIRE registry](https://inspire.ec.europa.eu/registry) provides a central access point to a number of centrally managed INSPIRE registers. The content of these registers are based on the INSPIRE Directive, Implementing Rules and Technical Guidelines.

## IATE

Interactive Terminology for Europe [IATE](https://iate.europa.eu/home) is the EU's terminology management system. It has been used in the EU institutions and agencies since summer 2004 for the collection, dissemination and management of EU-specific terminology. The project was launched in 1999 with the aim of providing a web-based infrastructure for all EU terminology resources, enhancing the availability and standardisation of the information.

## ANSIS

The Australian National Soil Information System provides a [complete vocabulary](https://ansis.net/standards/australian-soil-and-land-survey-field-handbook/) service on various aspects of the soil domain.

## WRB

Despite limited online presence various editions of the [World Reference Base](https://github.com/iuss-wrb/wrb) describe a classification system for soils, maintained by the WRB working group of IUSS.
Recent versions include a Fieldguide including a reange of classifications for soil properties (including lab procedures)

## Glosolan

[Standard Operating Procedures of the Global Soil Partnership](https://www.fao.org/global-soil-partnership/glosolan-old/soil-analysis/standard-operating-procedures/en/) are described in pdf's, not available in SKOS (yet) 

## NALT

[National Agricultural thesaurus](https://lod.nal.usda.gov/nalt/en/) is an initiative of USDA, it is widely used due to its completeness and acurateness

## AGRIS/CARIS
[AGRIS/CARIS](https://www.fao.org/4/u1808e/U1808E01.htm#TopOfPage): SUBJECT CATEGORIES AND SCOPE DESCRIPTIONS

In this Categorization Scheme, agriculture includes fisheries, forestry, food, nutrition and rural sociology. It comprises the production of plants and animals useful to man and the preparation and distribution of these products for man's use.


