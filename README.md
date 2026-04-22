# Soil Vocabs

Harmonising terminology within or between communities is an important aspect in cooperation. The SKOS ontology is a common mechanism to advertise (and link between) terminologies.  

On this repository we collect soil related vocabularies, glossaries, thesauri and ontologies. Also technologies to create, maintain and publish such vocabularies are collected here. The viewer to interact with such vocabularies is available at [Soil-Vocabs Viewer](https://soilwise-he.github.io/soil-vocabs/).

## Relevant terminologies

For the soil domain we should distinghuish various types of entities for which definitions can be listed.

- General glossary on soil related terms, what is soil, soil health, soil quality
- Soil **properties** / Soil health indicators to be monitored
- **Results**, in those cases that a result is a reference to a classification (low, medium, high) a proper definition of the class needs to be defined
- **Observation Procedures** describe how an observation has been performed
- The potential occurence of a soil **thread** can be determined by combining a number of indicators
- **Remediation procedures** describe how soil threads can be reduced
- Ability to perform Soil **functions** is estimated by the quality indicators
- Feature Of Interest **types**, an (set of) observation should be representative for a FOI, eg a horizon, profile, plot, site, body

## SoilWise Activities

- Design, test and document strategies on the use of SKOS when designing and publishing glossaries in Soil Mission projects
- [Soil Health Knowledge Graph](https://github.com/soilwise-he/soil-health-knowledge-graph) is a knowledge graph around soil health, based on EEA SoilHealth documentation
- [keyword matching](https://github.com/soilwise-he/metadata-augmentation/tree/main/keyword-matcher) uses synynyms and translations in agrovoc to match keywords on metadata records to a matched subset of keywords, to cluster records in filters
- [NER augmentation](https://github.com/soilwise-he/metadata-augmentation/tree/main/NER%20augmentation) is used to extract relevant keywords from the metadata record and its context
- [Soil-Vocabs](https://github.com/soilwise-he/soil-vocabs/tree/main/soil_health_benchmarks) contains some initiatives around improving soil vocabularies. Tooling to create a SKOS representation of a CSV with terms and definitions. And a [viewer to browse such a knowledge graph](https://soilwise-he.github.io/soil-vocabs/)
- A [vocview instance](https://voc.soilwise-he.containers.wur.nl/) to browse the Soil Health Knowledge Graph ([github](https://github.com/ternaustralia/vocview))
- Search strategies based on keyword relations in known vocabularies (broader, narrower, ...)

## Soil health Benchmarks

This repository includes an effort to convert the existing Benchmarks glossary to RDF.

Please go to [soil_health_benchmarks](./soil_health_benchmarks) for glossary to SKOS conversion and interlinking utilities.

## Tooling layout

The main published vocabulary files stay at the repository root, while support tooling lives in dedicated folders:

- `scripts/restore_soilvoc_from_csv.py` rebuilds or compares `SoilVoc.ttl` from `SoilVoc_concepts.csv`
- `scripts/generate_soilvoc_html.py` refreshes `assets/soilvoc_data.json` from `SoilVoc.ttl`
- `assets/VERSION` stores the viewer version used in the generated JSON payload
- `docker/Dockerfile` builds the combined API + static viewer container

Typical local commands:

```bash
python scripts/restore_soilvoc_from_csv.py --csv SoilVoc_concepts.csv --out SoilVoc_restored.ttl --compare SoilVoc.ttl
python scripts/generate_soilvoc_html.py
docker build -f docker/Dockerfile -t soilvoc .
```

## Soilwise-he project
This work has been initiated as part of the [Soilwise-he](https://soilwise-he.eu) project. The project receives
funding from the European Union’s HORIZON Innovation Actions 2022 under grant agreement No.
101112838. Views and opinions expressed are however those of the author(s) only and do not necessarily
reflect those of the European Union or Research Executive Agency. Neither the European Union nor the
granting authority can be held responsible for them.
