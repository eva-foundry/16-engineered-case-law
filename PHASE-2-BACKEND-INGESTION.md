# Phase 2: Backend Ingestion & UI Validation

**Status**: Current Priority  
**Date**: February 1, 2026  
**Prerequisites**: ✅ 419 ECL v2.1 files generated  
**Goal**: Validate end-to-end flow from ECL files → Backend → UI

---

## Overview

Phase 2 focuses on **proving the ingestion and retrieval workflow** before committing to source quality analysis. This validates that:
- ECL v2.1 format is compatible with backend processing
- Micro-headers enable effective chunking for RAG
- UI content management can display/search results correctly
- Retrieval quality is promising enough to justify deeper investment

---

## Objectives

### 1. Programmatic Backend Ingestion ⏳

**Goal**: Load ECL data into EVA DA backend without manual UI uploads.

**Tasks**:
- [ ] Identify EVA DA backend ingestion API/endpoint
  - Document: connection string, authentication method
  - Check: REST API vs SDK vs direct database access
- [ ] Create ingestion script (`pipeline/ingest_to_evada.py`)
  - Read ECL files from `out/ecl-v2/`
  - Parse 17-line headers + micro-header content
  - Submit to backend API with proper metadata
- [ ] Handle batch processing
  - Process 419 files in manageable batches (e.g., 50 at a time)
  - Implement retry logic for failures
  - Log ingestion status per file
- [ ] Verify backend receives data
  - Check backend logs/database
  - Confirm 419 records ingested
  - Validate metadata fields populated

**Success Criteria**:
- ✅ All 419 ECL files ingested without manual intervention
- ✅ Backend logs show successful processing
- ✅ No data corruption or truncation
- ✅ Ingestion time recorded (for performance baseline)

**Expected Challenges**:
- Authentication/permissions to backend
- API rate limiting or timeout issues
- Micro-header format compatibility with backend parser
- Large content size (max case ~1MB)

---

### 2. Backend Processing Validation ⏳

**Goal**: Verify backend correctly processes ECL v2.1 format.

**Tasks**:
- [ ] Inspect parsed metadata in backend
  - Verify 17 header fields extracted correctly
  - Check: CONTENT_HASH, KEYWORDS, TRIBUNAL_RANK, etc.
  - Validate date parsing (DECISION_DATE, GENERATED)
- [ ] Verify micro-header handling
  - Check if backend preserves micro-headers in content
  - OR: Check if backend strips and uses for chunk boundaries
  - Validate counter sequence maintained
- [ ] Inspect indexing results
  - Query backend index for sample case (e.g., SCC case)
  - Verify searchable fields populated (citation, tribunal, keywords)
  - Check vector embeddings generated (if applicable)
- [ ] Test chunk boundaries
  - Retrieve a single case, inspect how it's chunked
  - Verify micro-header boundaries respected (every ~1,500 chars)
  - Check chunk metadata includes case context

**Success Criteria**:
- ✅ All metadata fields correctly parsed and indexed
- ✅ Micro-headers either preserved or used for chunking
- ✅ Searchable by: citation, tribunal, keywords, date range
- ✅ Chunks contain full case context (self-describing)

**Validation Queries**:
```
1. Search: "2007 SCC 22" → Should return specific case
2. Search: "employment insurance misconduct" → Should return relevant cases
3. Filter: tribunal=SCC, language=EN → Should return SCC English cases only
4. Date range: 2020-2025 → Should return recent decisions
```

---

### 3. UI Content Management Inspection ⏳

**Goal**: Verify ECL content renders correctly in EVA DA UI.

**Tasks**:
- [ ] Navigate to content management section
- [ ] Locate ingested JP cases (419 records)
- [ ] Inspect sample case display
  - Header metadata visible and correct
  - Content readable (not garbled encoding)
  - Micro-headers visible (if preserved) or hidden (if stripped)
  - Source references (PDF_URI, BLOB_PATH) clickable/accessible
- [ ] Test search functionality
  - Keyword search returns expected results
  - Filters work (tribunal, language, date range)
  - Sorting works (by date, tribunal rank, relevance)
- [ ] Test pagination
  - Can navigate through all 419 cases
  - No duplicate records
  - No missing records

**Success Criteria**:
- ✅ All 419 cases visible in UI
- ✅ Metadata displayed correctly
- ✅ Content readable and properly formatted
- ✅ Search/filter/sort functions operational

**UI Smoke Tests**:
1. Search "Supreme Court" → Expect ~62 SCC cases
2. Filter by French language → Expect ~220 cases
3. Search "2024 FCA" → Expect recent Federal Court of Appeal cases
4. Click PDF_URI link → Should open CanLII PDF (external link)

---

### 4. Retrieval Quality Smoke Test ⏳

**Goal**: Quick validation that retrieval is "good enough" to proceed.

**Tasks**:
- [ ] Create 5 simple test queries (EI domain)
  - "voluntary leaving employment insurance"
  - "misconduct employment insurance canada"
  - "availability for work EI eligibility"
  - "just cause termination unemployment"
  - "illness leave employment insurance"
- [ ] Run queries through EVA DA chat interface
- [ ] Evaluate results informally:
  - Do top 5 results seem relevant?
  - Are citations correct (case names match content)?
  - Is language consistent (EN query → EN results)?
  - Are tribunal precedence hints visible (SCC > FCA > FC > SST)?
- [ ] Document observations
  - What works well?
  - What's missing or incorrect?
  - Any obvious retrieval failures?

**Success Criteria**:
- ✅ Queries return relevant cases (subjective but directional)
- ✅ Citations traceable to source cases
- ✅ No catastrophic failures (empty results, wrong language, crashes)
- ✅ Confidence to proceed with deeper quality analysis

**Expected Issues**:
- Retrieval may not be optimized yet (acceptable for PoC)
- Micro-header text might appear in results (cosmetic issue)
- Ranking may not respect tribunal precedence (needs scoring profile)

---

## Deliverables

### Code/Scripts
- [ ] `pipeline/ingest_to_evada.py` - Programmatic ingestion script
- [ ] `pipeline/validate_backend.py` - Backend validation queries (optional)
- [ ] `tests/test_retrieval_smoke.py` - Smoke test suite (optional)

### Documentation
- [ ] **Ingestion log** - Timestamped record of all 419 files ingested
- [ ] **Backend validation report** - Screenshots/logs of processed data
- [ ] **UI inspection report** - Screenshots of content management interface
- [ ] **Retrieval smoke test results** - Query/result pairs with observations

### Decision Artifacts
- [ ] **Go/No-Go for Phase 3** - Is retrieval quality promising enough?
- [ ] **Identified issues** - List of backend/UI issues to address
- [ ] **Performance baseline** - Ingestion time, query response time

---

## Risk Mitigation

### Risk 1: Backend API Not Available
**Mitigation**: 
- Check if direct database access possible (Azure Cosmos DB / SQL)
- Or: Use EVA DA SDK if available
- Fallback: Manual ingestion for 10 sample cases to validate UI

### Risk 2: Micro-Headers Break Backend Parser
**Mitigation**:
- Test with 5 cases first before batch ingestion
- Have fallback: strip micro-headers if needed
- Document issue for backend team to enhance parser

### Risk 3: Retrieval Quality Poor
**Mitigation**:
- This is a **finding**, not a failure
- Document specific issues (e.g., "SCC cases not ranked higher")
- Use findings to guide Phase 3 source quality analysis

### Risk 4: UI Can't Handle 419 Records
**Mitigation**:
- Start with 50 records batch
- Validate UI performance before full ingestion
- Scale up gradually (50 → 100 → 200 → 419)

---

## Timeline Estimate

| Task | Estimated Time | Dependencies |
|------|----------------|--------------|
| Identify backend API/auth | 2-4 hours | Access to backend docs/team |
| Build ingestion script | 4-8 hours | API documentation |
| Ingest 419 files | 1-2 hours | Script working, backend ready |
| Backend validation | 2-4 hours | Ingestion complete |
| UI inspection | 1-2 hours | Ingestion complete |
| Retrieval smoke test | 2-3 hours | Backend operational |
| Documentation | 2-3 hours | All tasks complete |

**Total**: 14-26 hours (~2-3 days)

---

## Success Metrics

**Phase 2 is DONE when:**
1. ✅ All 419 ECL files ingested programmatically
2. ✅ Backend correctly parses ECL v2.1 format
3. ✅ UI displays cases with correct metadata
4. ✅ Basic search/filter/sort works in UI
5. ✅ Retrieval smoke test shows promising results
6. ✅ Decision made: proceed to Phase 3 (source quality analysis)

---

## Next Phase Trigger

**Phase 2 → Phase 3 Transition:**

IF retrieval quality is "good enough" (subjective):
- Proceed to **Phase 3: Source Quality Analysis**
- Compare JSON vs PDF vs HTML content quality
- Select canonical source based on evidence

IF retrieval quality is poor:
- **Pause and debug** before Phase 3
- Investigate: Is it the source data? The chunking? The indexing?
- Fix issues before investing in source quality analysis

---

## Open Questions

1. **Backend API Endpoint**: What is the ingestion API URL?
2. **Authentication**: What credentials/tokens needed?
3. **Rate Limits**: Any API throttling we need to handle?
4. **Micro-Header Handling**: Does backend parse or ignore them?
5. **Chunk Size**: Does backend have max chunk size limits?
6. **Vector Embeddings**: Are they auto-generated or must we provide?
7. **Index Name**: What index/collection should we target?

**Action**: Schedule meeting with EVA DA backend team to answer these questions.

---

## Contact Points

**Backend Team**: [TBD - who maintains EVA DA backend?]  
**UI Team**: [TBD - who maintains content management interface?]  
**Project Owner**: [TBD]

---

**Document Version**: 1.0  
**Last Updated**: February 1, 2026  
**Status**: Active - Phase 2 in progress
