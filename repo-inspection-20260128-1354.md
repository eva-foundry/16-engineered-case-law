
This project I:\EVA-JP-v1.2\docs\eva-foundation\projects\16-engineered-case-law
CDC project I:\EVA-JP-v1.2\docs\eva-foundation\projects\15-cdc
InfoJP project repo I:\EVA-JP-v1.2\docs\eva-foundation\projects\11-MS-InfoJP

---

## **STATUS UPDATE (February 1, 2026)**

**Strategic decisions made since this discovery document:**

✅ **Questions 1-3 Answered via PoC Strategy:**
- **Deferred CDC** - Using SQLite JSON as convenience source to validate ECL pipeline first
- **Deferred source quality analysis** - JSON vs PDF/HTML comparison **pending**
- **ECL pipeline validated** - 419 cases generated with micro-header system (see README §8)

⏳ **Questions 4-6 Now Current Focus:**
- **Backend ingestion next** - Load ECL data programmatically into EVA DA
- **UI validation next** - Verify content management and retrieval in UI
- **Gold set testing pending** - After backend/UI validation

⚠️ **Critical Decision Point Ahead (Phase 3):**
- **Must compare** JSON vs PDF vs HTML content quality before production
- **Source selection** deferred until quality analysis complete
- **OCR requirements** not yet assessed (% of PDFs image-only)

📋 **PoC Strategy:**
1. ✅ Phase 1: Validate ECL pipeline with SQLite convenience data (DONE)
2. ⏳ Phase 2: Backend ingestion + UI testing (CURRENT)
3. ⏳ Phase 3: Source quality analysis (DECISION POINT)
4. ⏳ Phase 4: Implement canonical source based on evidence
5. ⏳ Phase 5: CDC integration for production scale

---

**Original discovery questions below remain valid for Phase 3 work ↓**

---

## 1) Are the PDFs image-only or text-searchable (do we need OCR)?

**Goal:** estimate what % of the 25k PDFs have a usable text layer vs require OCR.

### What to do (practical inspection method)

Run a **sampling scan** against Blob:

* Randomly sample (e.g., 300–1,000 PDFs across tribunals/years)
* For each PDF:

  * Extract text with a standard extractor (pdfminer/pypdf)
  * Apply “quality gates”:

    * non-empty
    * reasonable length
    * readable character distribution
    * coverage beyond first page (to avoid “title-only” extraction)

This matches your proposed “OCR only when gates fail” approach (and keeps OCR proportional to *failure rate*, not total pages). The CDC schema explicitly supports recording the extraction method (`pdf_text` vs `ocr`) plus an optional `quality_score` and warnings per case/language. 

**Output of this step:**

* % searchable-text PDFs (pass gates)
* % OCR-needed PDFs (fail gates)
* by tribunal + year (so you can forecast cost and prioritize)

---

## 2) Once Q1 is known: should JSON text or PDF extraction be the source of truth?

Use this rule:

### Canonical truth model

**Truth = “best-evidence canonical text” per language, traceable to an artifact.**

Your CDC schema literally models this as `case_text`, with:

* `text_source_artifact_id`
* `extraction_method` = `html_parse | pdf_text | ocr`
* `normalized_text_hash`
* optional `quality_score` and `warnings` 

### Decision logic (simple and defensible)

* If PDFs are mostly searchable and pass gates → **PDF text becomes canonical** (lowest governance risk: you’re indexing the primary artifact).
* If your existing JSON text is high quality and already extracted → it can be canonical **if** you can still link it to the PDF artifact/version and record method + quality score (i.e., treat JSON as “already-produced `case_text`”).
* If they disagree → prefer the one with:

  1. higher quality score / fewer warnings
  2. better page coverage / fewer OCR artifacts
  3. stronger provenance (artifact hash/versioning)

That keeps “source of truth” **auditable and replayable**, which is a core CDC design principle. 

---

## 3) Generate the engineered case law so EVA DA chunks correctly

In CDC terms, “engineered case law” is produced in the downstream actions chain:

* `extract_text` (or accept existing canonical text)
* `generate_chunks` (deterministic + delta-friendly)
* `embed_chunks`
* `update_index` 

Two key requirements for engineered case law to work well in EVA DA:

1. **Deterministic chunk IDs + stable structure**
   So reprocessing doesn’t duplicate/fragment. (This is called out as an implementation decision: idempotent processing with deterministic chunk IDs and upsert semantics.) 

2. **Index fields that retrieval can actually use**
   At minimum: `case_id`, `tribunal`, `decision_date`, `language`, `source_uri`, plus freshness fields if you want recency boosting. 

---

## 4) Test EVA DA with engineered case law content

A clean test is to run **two indexes/projects** (JP-EN, JP-FR) with the engineered chunks, then execute a fixed test pack of queries:

* known EI adjudication issues (misconduct, availability, voluntary leaving, etc.)
* expected top cases (gold set)
* require citable passages (no paraphrase requirement)

CDC already frames the mechanics you need: changes trigger `update_index` and metadata-only updates when appropriate. 

---

## 5) Does it work? What to change in EVA DA? How to measure quality?

### What “quality” means here (in a way you can measure)

1. **Retrieval quality**

* Precision@K / Recall@K against a small gold set
* “Correct tribunal precedence” appearing in top-K
* Language match rate (EN query returns EN chunks)

2. **Citation correctness**

* Answer includes verbatim-supporting excerpts (or near-verbatim) and stable citations

3. **Freshness / drift resistance**

* staleness lag (how far behind newest decisions you are)
* coverage % (indexed docs vs source inventory)

Your CDC docs already anticipate freshness metrics + recency-aware scoring profiles in Azure AI Search (so EVA DA retrieval actually benefits from CDC freshness). 

### What to change in EVA DA (only if tests show it)

* **Search scoring profile**: enable freshness boost + authority score weighting (court precedence). 
* **Filter policy**: enforce `is_deleted eq false` and language filters.
* **Prompting**: enforce “cite, don’t paraphrase” behavior at response time (your business requirement).

---

## 6) Would we use EVA DA APIs exposed by backend?

Yes — and CDC’s downstream contract essentially assumes that:

* the pipeline ends with `update_index` (upsert to Azure AI Search) 
* EVA DA’s runtime uses hybrid search against that index (vector + keyword), optionally with a scoring profile for freshness/authority. 

So the “API surface” question becomes:

* **Ingestion path**: either push documents/chunks through EVA DA’s ingestion endpoints (if available), *or* write directly to the underlying Azure AI Search index the backend reads from (often simplest for controlled prototypes).
* **Query path**: use EVA DA backend chat/retrieval endpoints so you’re testing *the real orchestration* (retrieval + prompting + citation formatting), not just raw search.

---

If you want the tight next action list (no extra theory), it’s:

1. **Blob PDF sample scan** → % OCR-needed vs searchable-text
2. Choose canonical text policy using `case_text` (method + quality score) 
3. Generate engineered case law chunks (`generate_chunks`) and upsert (`update_index`) 
4. Run a gold-set evaluation + track freshness/coverage metrics 
5. Decide whether EVA DA needs scoring/filter/prompt adjustments

