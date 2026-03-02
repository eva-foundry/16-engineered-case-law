
# JP Engineered Case Law

## README → CDC Pipeline Tasks & Stories Mapping

---

## EPIC 1 — CanLII Inventory & CDC Foundation

**README Sections:**

* §1 Context and Problem
* §3 Core Principles
* §4 High-Level Ingestion Flow

### Feature 1.1 — CanLII Inventory Snapshotting

**CDC Component**

* Poll Executor
* Case Registry
* poll_run table

**Stories**

* **STORY 1.1.1** – Create CanLII inventory snapshot

  * Retrieve full CanLII link inventory
  * Persist snapshot with timestamp + scope_id
* **STORY 1.1.2** – Diff inventory snapshots

  * Identify new / changed / unchanged cases
  * Emit `change_event` records (structural / availability)

**Downstream Actions**

```
update_registry
```

**Evidence / DoD**

* poll_run created even if no changes
* snapshot + diff persisted and queryable

---

## EPIC 2 — Artifact Acquisition (PDF + HTML)

**README Sections:**

* §5 Artifact Strategy
* §7 Bilingual Handling (input side)

### Feature 2.1 — PDF & HTML Fetching

**CDC Component**

* Artifact Index
* fetch_artifact action

**Stories**

* **STORY 2.1.1** – Fetch PDFs for new/changed cases

  * Download once per version
  * Hash + timestamp
* **STORY 2.1.2** – Fetch HTML for metadata only

  * Store HTML separately
  * Mark as non-authoritative content

**Downstream Actions**

```
fetch_artifact
```

**Evidence / DoD**

* artifact table populated
* duplicate downloads prevented by hash reuse

---

## EPIC 3 — PDF Inspection & OCR Decisioning

**README Sections:**

* §6 Text Extraction Strategy

### Feature 3.1 — PDF Text Inspection

**CDC Component**

* Text Enrichment
* extract_text action

**Stories**

* **STORY 3.1.1** – Attempt PDF text extraction

  * No OCR by default
* **STORY 3.1.2** – Apply quality gates

  * length
  * character distribution
  * page coverage
* **STORY 3.1.3** – Trigger OCR only when gates fail

**Downstream Actions**

```
extract_text
```

**Evidence / DoD**

* extraction_method recorded per case/lang
* OCR usage proportional to failure rate

---

## EPIC 4 — Canonical Case Text Selection

**README Sections:**

* §8.1 Canonical Case Text

### Feature 4.1 — Canonical Text Resolution

**CDC Component**

* case_text
* change_event (content / availability)

**Stories**

* **STORY 4.1.1** – Resolve canonical text per language

  * PDF-derived vs existing JSON
* **STORY 4.1.2** – Record provenance

  * artifact_id
  * extraction_method
  * content hash
* **STORY 4.1.3** – Enforce language-as-variant rule

**Downstream Actions**

```
extract_text
(update only if changed)
```

**Evidence / DoD**

* deterministic canonical text
* replay produces same result

---

## EPIC 5 — Bilingual Detection & Handling

**README Sections:**

* §7 Bilingual Handling

### Feature 5.1 — Language Policy Enforcement

**CDC Component**

* language-policy.yaml
* availability change class

**Stories**

* **STORY 5.1.1** – Detect EN / FR / BI composition
* **STORY 5.1.2** – Attempt deterministic split
* **STORY 5.1.3** – Tag bilingual when split unreliable

**Downstream Actions**

```
extract_text
(update_index_metadata_only)
```

**Evidence / DoD**

* no silent language inference
* bilingual explicitly tagged

---

## EPIC 6 — Engineered Case Law Generation (Chunking)

**README Sections:**

* §8.2 Deterministic Chunking

### Feature 6.1 — Chunk Engineering

**CDC Component**

* generate_chunks
* embed_chunks

**Stories**

* **STORY 6.1.1** – Generate deterministic chunks

  * stable boundaries
  * stable chunk_id
* **STORY 6.1.2** – Attach legal metadata

  * case_id
  * tribunal
  * decision_date
  * language
* **STORY 6.1.3** – Delta-only chunk regeneration

**Downstream Actions**

```
generate_chunks
embed_chunks
```

**Evidence / DoD**

* re-run does not duplicate chunks
* only changed chunks re-embedded

---

## EPIC 7 — EVA DA Index Ingestion

**README Sections:**

* §9 EVA DA Ingestion and Testing

### Feature 7.1 — Index Updates

**CDC Component**

* update_index
* update_index_metadata_only

**Stories**

* **STORY 7.1.1** – Upsert engineered chunks
* **STORY 7.1.2** – Metadata-only updates when applicable
* **STORY 7.1.3** – Soft-delete withdrawn cases

**Downstream Actions**

```
update_index
update_index_metadata_only
mark_withdrawn_or_deleted
```

**Evidence / DoD**

* index reflects CDC state
* no full reindex on metadata-only change

---

## EPIC 8 — EVA DA Validation & Quality Measurement

**README Sections:**

* §10 Measuring “Does This Work?”

### Feature 8.1 — Retrieval & Citation Validation

**CDC Component**

* acceptance-tests.md
* EVA DA backend APIs

**Stories**

* **STORY 8.1.1** – Execute gold-set queries
* **STORY 8.1.2** – Validate tribunal precedence
* **STORY 8.1.3** – Validate verbatim citation behavior

**Evidence / DoD**

* Precision@K documented
* citation traceable to chunk → artifact

---

## EPIC 9 — Freshness, Coverage & Governance

**README Sections:**

* §10.3 Freshness and Coverage
* §11 Known Risks

### Feature 9.1 — Freshness Telemetry

**CDC Component**

* corpus_registry
* poll_run metrics

**Stories**

* **STORY 9.1.1** – Track coverage %
* **STORY 9.1.2** – Measure staleness lag
* **STORY 9.1.3** – Report CDC health

**Downstream Actions**

```
(record metrics only)
```

**Evidence / DoD**

* freshness visible per corpus
* SLO tier respected

---

## One-Line Summary (for Exec / Gate Review)

> The Engineered Case Law README maps **1:1** to CDC pipeline actions — from CanLII discovery through deterministic chunking and EVA DA ingestion — with every step governed by policy, traceable via change_event evidence, and measurable for quality and freshness.

