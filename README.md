# Sub-Knowledge Graph Extraction Algorithm

## Overview

This repository implements a novel algorithm for extracting domain-specific sub-knowledge graphs from large, generic knowledge graphs. The algorithm combines seed-based graph traversal with Large Language Model (LLM) relevance classification to identify and extract coherent topical subgraphs while preserving semantic relationships.

## Objective

Given a large knowledge graph containing diverse domains (e.g., AGROVOC with 40,000+ concepts spanning agriculture, forestry, fisheries, environment), our algorithm aims to:

1. **Extract a focused sub-KG** centered around a specific topic (e.g., "soil science")
2. **Maintain semantic coherence** by preserving relevant relationships while pruning peripheral concepts
3. **Leverage both structural and semantic information** through SKOS hierarchical relationships and LLM understanding
4. **Achieve efficient extraction** by minimizing computational overhead through intelligent batching and automatic inference

## Algorithm Design

### Core Approach: Iterative Graph Traversal with Semantic Filtering

The algorithm performs breadth-first traversal from a seed node, using LLMs to classify the relevance of neighboring nodes at each step. This combines the structural information from the graph with semantic understanding from language models.

### Two Main Strategies

#### Strategy 1: LLM-Based Relevance Classification

* Query one-hop neighbors of candidate nodes
* Batch nodes for efficient LLM processing (30-50 nodes per batch)
* LLM evaluates each node based on semantic relevance to the seed topic
* Classification produces binary decision (INCLUDE/EXCLUDE) with confidence score [0,1]

#### Strategy 2: Automatic Hierarchical Inclusion

* For high-confidence nodes (≥0.90), automatically include entire skos:narrower hierarchy
* Leverages SKOS semantic guarantee that narrower terms are specializations within the same domain
* Eliminates need for LLM evaluation of definitionally relevant terms
* Significantly reduces API calls while maintaining precision

## Step-by-Step Algorithm

### 1. Initialization

```
- Input: Seed node (e.g., "soil")
- Initialize: 
  - Frontier = {seed_node}
  - Visited = ∅
  - SubKG = {seed_node} with confidence = 1.0
```

### 2. Iterative Expansion

**While** Frontier is not empty:

#### 2.1 Node Retrieval

* For each node in Frontier:
  * Query all one-hop neighbors via SPARQL
  * Retrieve prefLabel and altLabels for each neighbor
  * Exclude already visited nodes

#### 2.2 Batch Processing

* Group unvisited neighbors into batches of 30-50 nodes
* Format: `prefLabel | altLabel1; altLabel2; ...`

#### 2.3 LLM Classification

For each batch, LLM evaluates based on:

* ​**Inclusion Criteria**​:
  * Core concepts and properties of seed topic
  * Direct measurements and classifications
  * Study methods and management practices specific to topic
  * Information and data about the topic
  * Direct interventions and intrinsic processes
* ​**Exclusion Criteria**​:
  * Semantic irrelevance or overly broad scope
  * Primary domain elsewhere
  * Generic terms without specific connection
  * Distant consequences or effects

#### 2.4 Confidence-Based Processing

For each classified node:

* If `classification == "INCLUDE"`:
  * If `confidence >= 0.90`:
    * Recursively query and include ALL skos:narrower descendants
    * Mark descendants with confidence = 1.0
    * Add to SubKG without LLM evaluation
  * If `confidence < 0.90`:
    * Add node to SubKG
    * Add to next iteration's Frontier for exploration
* If `classification == "EXCLUDE"`:
  * Skip node and do not explore its neighbors

#### 2.5 Update State

* Add processed nodes to Visited
* Update Frontier with newly included nodes (excluding high-confidence hierarchies)

### 3. Termination

Algorithm terminates when:

* Frontier is empty (no new relevant nodes to explore)
* OR maximum depth/iteration limit reached
* OR subgraph size exceeds threshold

## Key Design Decisions

### Batch Size Optimization

* **30-50 nodes per LLM call** balances:
  * Attention mechanism effectiveness
  * API efficiency
  * Classification consistency
  * Error recovery capability

### Confidence Threshold Calibration

* ​**≥0.90**​: Triggers automatic hierarchy inclusion
  * Reserved for unambiguous domain concepts
  * Examples: "soil types", "soil composition", "soil properties"
* ​**0.75-0.89**​: High relevance but requires individual narrower term evaluation
* ​**0.60-0.74**​: Moderate confidence, included but carefully evaluated
* ​**<0.60**​: Generally excluded

### Handling Edge Cases

#### Compound Terms

* Terms containing seed topic (e.g., "soil sampling", "soil information")
* Default to inclusion unless clear domain shift

#### Cross-Domain Bridges

* Terms at domain interfaces (e.g., "rhizosphere" between soil and plant biology)
* Classified based on primary conceptual home

## Experimental Results

### Test Case: "Soil" as Seed Node

Two critical observations demonstrate the algorithm's effectiveness:

### Observation 1: Natural Convergence

Despite setting a maximum of 20 iterations, the algorithm naturally terminated after just 10 iterations by exhausting relevant nodes to explore. This demonstrates successful pruning that prevents unbounded graph expansion—the algorithm's greatest risk.

**Iteration-by-Iteration Statistics (Strategy 1):**

```
Iteration 1:  23 evaluated,  16 included (69.6%),   7 excluded
Iteration 2:  67 evaluated,  41 included (61.2%),  26 excluded
Iteration 3: 244 evaluated, 140 included (57.4%), 104 excluded
Iteration 4: 388 evaluated, 190 included (49.0%), 196 excluded  ← Peak exploration
Iteration 5: 390 evaluated, 205 included (52.6%), 185 excluded  ← Peak evaluation
Iteration 6: 307 evaluated, 129 included (42.0%), 178 excluded  ← Declining frontier
Iteration 7: 215 evaluated,  71 included (33.0%), 144 excluded
Iteration 8:  95 evaluated,  75 included (78.9%),  20 excluded
Iteration 9:  24 evaluated,   9 included (37.5%),  15 excluded
Iteration 10: 14 evaluated,   4 included (28.6%),  10 excluded  ← Natural termination
```

**Key Insights:**

* Exploration peaks at iterations 4-5 then rapidly converges
* Inclusion rate decreases in later iterations, indicating effective boundary detection
* Total nodes evaluated: 1,767
* Total nodes included: 880 (49.8% overall inclusion rate)

### Observation 2: Strategy Consistency Validation

When comparing Strategy 2 (with automatic hierarchical inclusion) against Strategy 1:

**Automatic Inclusion Statistics:**

* Total nodes included in Strategy 2: **809 nodes**
* Nodes auto-included via hierarchy: **210 nodes** (26% of total)

**Cross-Strategy Validation of Auto-Included Nodes:**

```
✓ Also included in Strategy 1:  181 nodes (86.2%)
✗ Pruned in Strategy 1:          15 nodes  (7.1%)
⊘ Never visited in Strategy 1:   14 nodes  (6.7%)
```

**Interpretation:**

* **86.2% agreement** between automatic inclusion and LLM classification validates the hierarchical assumption
* Only 7.1% false positives (nodes that should have been pruned)
* 6.7% represents deeper hierarchies not reached by Strategy 1's traversal

### Performance Metrics

Based on the cross-strategy comparison:

* ​**Precision of Auto-Inclusion**​: \~93% (considering pruned nodes as errors)
* ​**Consistency Rate**​: 86.2% (direct agreement between strategies)
* ​**Efficiency Gain**​: 210 fewer LLM evaluations (26% reduction in API calls)

These results demonstrate that:

1. The algorithm effectively prevents exponential graph expansion through intelligent pruning
2. LLM classifications are highly consistent with SKOS hierarchical semantics
3. The dual-strategy approach offers both thoroughness and efficiency

## To-do
