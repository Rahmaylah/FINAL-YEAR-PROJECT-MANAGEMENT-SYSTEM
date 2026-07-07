# Phase 2: Duplicate Detection & Intelligence - Implementation Roadmap

## The Story: How Duplicate Detection Will Work

Imagine you're building a smart librarian for final year projects. This librarian doesn't just look at titles - it understands meaning, catches clever rephrasings, and learns from experience. Here's how we'll build this intelligent system:

## 📚 The Big Picture

Our duplicate detection system will be a **hybrid intelligence** that combines three approaches:
- **Semantic Understanding**: Catches rephrased content ("AI chatbot" vs "conversational AI bot")
- **Lexical Matching**: Finds exact word overlaps and typos
- **Hybrid Scoring**: Combines both with configurable weights

## 🗺️ Implementation Roadmap

### **Step 1: Foundation - Embedding Infrastructure** ✅ COMPLETED
**Goal**: Set up the AI brain that understands project meaning

**What we built:**
- ✅ `projects/utils.py` - Core embedding functions with Sentence-BERT (all-mpnet-base-v2, 768-dim)
- ✅ Django signals to auto-generate embeddings when projects are created/updated
- ✅ Management command `generate_embeddings` for batch processing existing projects
- ✅ Verified working - embeddings stored successfully in PostgreSQL pgvector columns

**How it works:**
1. When a student submits "AI-powered Chat Bot using Transformers"
2. System generates 768-dimensional vectors for title, objectives, and combined text
3. Vectors are stored in PostgreSQL with pgvector extension
4. Similar projects have "close" vectors in mathematical space

### **Step 2: Similarity Detection Engine** 🔄 IN PROGRESS
**Goal**: Build the algorithms that find duplicates

**What we're building:**
- `projects/similarity.py` with SimilarityScorer class (structure exists, needs completion):
  - **Semantic Search**: Vector similarity using cosine distance
  - **Lexical Search**: PostgreSQL full-text search with ranking
  - **Hybrid Scoring**: Weighted combination (70% semantic + 30% lexical)

**Status**: Core class exists with methods, needs wiring into API endpoints

**How it works:**
```
New Project: "Machine Learning for Image Recognition"

1. SEMANTIC: Find projects with similar meaning
   → "Computer Vision using ML" (high similarity)
   → "Weather prediction model" (low similarity)

2. LEXICAL: Find projects with similar words
   → "ML image classification project" (word overlap)
   → "Database management system" (no overlap)

3. HYBRID: Combine scores with weights
   → Final score: 0.85 (above threshold → flag for review)
```

### **Step 3: API Integration** 📅 NEXT
**Goal**: Make duplicate detection accessible via REST API

**What needs to be done:**
- `POST /api/projects/{id}/duplicate_check/` - Manual trigger (placeholder exists, needs implementation)
- `POST /api/projects/bulk_duplicate_check/` - Process multiple projects (needs creation)
- `POST /api/duplicate-flags/{id}/mark_reviewed/` - Admin review workflow (skeleton exists)

**How it works:**
```
Student submits project → System automatically:
1. Generates embeddings
2. Searches for similar projects
3. If similarity > 0.8: Auto-flag as duplicate
4. If similarity 0.6-0.8: Flag for mentor review
5. If similarity < 0.6: Approve automatically
```

### **Step 4: Management & Configuration** 🔄 PARTIAL
**Goal**: Make the system tunable and maintainable

**What we've built:**
- ✅ Django settings for thresholds and weights (default values in code)
- ✅ Management commands for batch operations (`generate_embeddings`)
- ✅ Logging for embedding generation

**What needs work:**
- Admin interface for reviewing flagged duplicates (needs Django admin setup)
- Advanced monitoring and metrics

**Configuration options:**
```python
DUPLICATE_SIMILARITY_THRESHOLD = 0.6    # Flag for review
DUPLICATE_AUTO_FLAG_THRESHOLD = 0.8     # Auto-flag as duplicate
SEMANTIC_WEIGHT = 0.7                   # 70% semantic, 30% lexical
SEARCH_YEARS_BACK = 3                   # Check last 3 years
```

## 🔄 The Detection Workflow

### **Real-time Detection (On Project Submission)**
```
1. Student submits project
2. System generates embeddings (2-3 seconds)
3. Searches vector database for similar projects (< 200ms)
4. Applies full-text search for lexical matches (< 100ms)
5. Combines scores with configured weights
6. Applies decision rules:
   - Score < 0.6: ✅ Auto-approve
   - 0.6 ≤ Score < 0.8: ⚠️ Flag for mentor review
   - Score ≥ 0.8: 🚫 Auto-flag as duplicate
7. Creates DuplicateFlag record if needed
8. Returns result to frontend
```

### **Batch Detection (Admin Operation)**
```
1. Admin runs: python manage.py batch_detect_duplicates
2. System processes all projects without embeddings
3. Generates missing embeddings
4. Compares each project against all others
5. Creates DuplicateFlag records for matches above threshold
6. Generates report of flagged duplicates
```

## 🎯 Technical Architecture

### **Data Flow**
```
Project Text → Sentence-BERT → 768D Vector → pgvector → Similarity Search → Score → Decision
```

### **Performance Targets**
- **Embedding Generation**: 2-3 seconds per project
- **Similarity Search**: < 200ms for 10K projects
- **Storage**: ~11KB per project (embeddings + metadata)
- **Accuracy**: 85%+ detection rate with <5% false positives

### **Scalability**
- **Current**: 100 projects → ~1MB storage
- **Future**: 10K projects → ~1GB storage, <500ms search
- **Optimization**: IVFFlat indexes, table partitioning by year

## 🧪 Testing & Validation Strategy

### **Unit Tests**
- Test embedding generation accuracy
- Test similarity calculations
- Test threshold logic

### **Integration Tests**
- End-to-end duplicate detection workflow
- API endpoint testing
- Management command testing

### **Validation Data**
- Create known duplicate pairs for testing
- Measure precision/recall metrics
- A/B test different threshold combinations

## 🚀 Success Metrics

- **Detection Rate**: 85%+ of actual duplicates caught
- **False Positive Rate**: <5% of flagged projects are not duplicates
- **Processing Speed**: <3 seconds per submission
- **Admin Review Load**: 60% reduction in manual duplicate checking

## 📋 Implementation Order

1. **Week 1**: ✅ COMPLETED - Embedding infrastructure (`utils.py`, signals, management command)
   - EmbeddingService class fully implemented with Sentence-BERT
   - Django signals auto-generate embeddings on project save
   - Management command `generate_embeddings` created and tested
   - Verified embeddings stored in database (768-dimensions)

2. **Week 2**: ✅ COMPLETED - Similarity algorithms
   - ✅ SimilarityScorer class fully implemented in `similarity.py`
   - ✅ Hybrid scoring combines semantic (70%) + lexical (30%)
   - ✅ Fixed pgvector normalization to handle JSON string format from raw SQL

3. **Week 3**: ✅ COMPLETED - API endpoints and integration
   - ✅ Implemented `ProjectViewSet.duplicate_check()` action with full scoring
   - ✅ Implemented `bulk_duplicate_check()` endpoint for batch processing
   - ✅ Moved duplicate check into post_save signal for auto-flagging on all creation methods
   - ✅ Admin panel enhanced with color-coded scores and similar projects display

4. **Week 4**: 📅 NEXT - Testing, optimization, and documentation

This roadmap gives us a smart, scalable duplicate detection system that learns from project content and reduces manual work while maintaining accuracy. The hybrid approach ensures we catch both obvious duplicates and clever rephrasings that students might try.

---

## 📖 Additional Context

### **Why Hybrid Approach?**
- **Semantic-only**: Catches rephrasings but slow and resource-intensive
- **Lexical-only**: Fast but misses paraphrases and synonyms
- **Hybrid**: Best of both worlds - accurate and performant

### **Model Choice: Sentence-BERT**
- **all-MiniLM-L6-v2**: 384 dimensions, fast, good accuracy
- **all-mpnet-base-v2**: 768 dimensions, slower, higher accuracy
- **Recommendation**: Start with all-mpnet-base-v2 for production use

### **Threshold Tuning**
- **Conservative (0.8)**: Fewer false positives, more manual review
- **Aggressive (0.6)**: More automation, higher false positive risk
- **Balanced (0.7)**: Good compromise for most use cases

### **Edge Cases to Handle**
- Very short titles (< 10 words)
- Technical jargon and domain-specific terms
- Multilingual content
- Mathematical/formula content
- Code snippets in descriptions

### **Monitoring & Maintenance**
- Track detection accuracy over time
- Monitor processing performance
- Regular model updates for new terminology
- Admin feedback loop for threshold adjustments

---

*Document created: April 4, 2026*
*Last updated: April 4, 2026*</content>
<parameter name="filePath">/home/revocajana/projects/fypms/docs/DUPLICATEDETECTOR_ROADMAP.md
