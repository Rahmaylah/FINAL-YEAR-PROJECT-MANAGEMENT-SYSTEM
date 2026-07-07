# FYPMS - TODO List

## ✅ Phase 1: Core Features (COMPLETED)
- [x] Database schema design (PostgreSQL with pgvector support)
- [x] Django models creation (Project, ProjectType, ProjectUser, DuplicateFlag, User with roles)
- [x] REST API endpoints (CRUD operations - ViewSets for Users, Projects, ProjectUsers, DuplicateFlags, ProjectTypes)
- [x] Authentication setup (Session-based login via `/api/login/` endpoint)
- [x] Admin panel configuration (Django admin interface available)
- [x] Basic React frontend (Login, Dashboards for Student/Mentor/Coordinator)
- [x] Project structure and dependencies setup
- [x] User role system (Student, Mentor, Coordinator roles with permissions)
- [x] ProjectUser model for group project support
- [x] Basic API filtering (year, status, is_flagged_duplicate)
- [x] CORS configuration for React frontend

---

## ✅ Phase 2: Duplicate Detection & Intelligence (COMPLETED)
### **Status:** Full end-to-end duplicate detection system implemented and validated
- ✅ Hybrid similarity scoring (70% semantic + 30% lexical)
- ✅ Auto-flagging on project creation with score tracking
- ✅ Fixed pgvector normalization: handles JSON string format from raw SQL
- ✅ Validated: 4 identical projects auto-flagged with scores 0.9944-1.0

#### **Implement Embedding Generation** 
- [x] Create `projects/utils.py` with embedding generation functions
- [x] Integrate sentence-transformers for project embeddings (all-mpnet-base-v2 - 768 dims)
- [x] Create functions:
  - [x] `generate_embeddings(text)` - Generate embedding from text
  - [x] `generate_project_embeddings(project)` - Generate all embeddings for a project
  - [x] `batch_embed_all_projects()` - Batch embed existing projects
- [x] Generate embeddings on project creation/update using Django signals
- [x] Store embeddings in pgvector columns (title_embedding, objectives_embedding, combined_embedding - all 768 dimensions)
- [x] Create management command `python manage.py generate_embeddings` for batch generation
- [x] Verify pgvector extension is enabled in PostgreSQL (`CREATE EXTENSION IF NOT EXISTS vector`)

#### **Implement Duplicate Detection Algorithm**
- [x] Create `projects/similarity.py` with SimilarityScorer class
  - [x] `calculate_semantic_similarity()` - Cosine similarity between embeddings
  - [x] `calculate_lexical_similarity()` - PostgreSQL full-text search with ranking
  - [x] `calculate_hybrid_similarity()` - Combined score (70% semantic + 30% lexical)
  - [x] `find_similar_projects()` - Find and score duplicates for single project
  - [x] `_normalize_embedding()` - Handle multiple embedding input types (JSON strings, numpy arrays, lists)

#### **Duplicate Handling API Endpoints**
- [x] Implement `POST /api/projects/{id}/duplicate_check/` - Manual trigger with similarity breakdown
- [x] Create `POST /api/projects/bulk_duplicate_check/` - Bulk duplicate detection
- [x] Implement `POST /api/duplicate-flags/{id}/mark_reviewed/` - Mark as reviewed
- [x] Wire up DuplicateFlag creation when similarity above threshold
- [x] Add API response with detailed similarity breakdown (semantic + lexical scores)

#### **Configuration & Management**
- [x] Add Django settings for similarity thresholds (similarity_threshold=0.6, auto_flag_threshold=0.8)
- [x] Create management command `python manage.py bulk_duplicate_check` 
- [x] Add management command `python manage.py generate_embeddings`
- [x] Add logging for duplicate detection operations

---

## 🟡 Phase 3: Search & Filtering (BACKEND API EXISTS, FRONTEND MISSING)

### **Backend Search (API Layer) - Mostly Complete**
- [x] Basic project filtering by year, status, is_flagged_duplicate (API supports)
- [x] Pagination via DRF default pagination
- [ ] Full-text search endpoint `GET /api/projects/search/?q=query` (needs implementation)
  - [ ] Use PostgreSQL full-text search with ranking
  - [ ] Search title, main_objective, project_description, implementation_details
  - [ ] Return results ranked by relevance

### **Frontend Search UI - NOT DONE**
- [ ] Add search bar to StudentDashboard for project discovery
- [ ] Add filter UI (year, status, duplicate flag)
- [ ] Display search results with pagination
- [ ] Show relevance score/ranking for search results

### **Appointment Features - Model exists but needs work**
- [ ] Create Appointment model (not yet in database)
  - [ ] Fields: student, mentor, date, status (proposed/confirmed/completed/cancelled), notes
- [ ] Appointment API endpoints (list, create, update status)
- [ ] Filter by status and date range
- [ ] Calendar integration (React Calendar or similar)

---

## 🟡 Phase 4: Frontend Enhancements (DASHBOARDS EXIST, NEEDS IMPROVEMENTS)

### **Project Management UI - PARTIALLY DONE**
- [x] Project submission form in StudentDashboard (form exists, save works)
- [x] Basic form fields (title, objective, description, implementation)
- [ ] **Project listing with filters**
  - [ ] Create `ProjectList.js` component for StudentDashboard
  - [ ] Display all projects student can see (own + public)
  - [ ] Add year/status filter dropdowns
  - [ ] Pagination for large datasets
- [ ] **Project detail view**
  - [ ] Create `ProjectDetail.js` component
  - [ ] Show full project info including mentor name
  - [ ] Display similarity score if flagged
  - [ ] Edit/delete buttons (for owner)
- [ ] Form validation and error handling improvements
- [ ] File upload for project attachments (if needed)

### **Dashboard Improvements**
- [ ] Add project counts and statistics to all dashboards
- [ ] Implement notification system for status changes
- [ ] Add export functionality for coordinators
- [ ] Improve mobile responsiveness
- [ ] Add loading states and error handling throughout

### **Additional Features**
- [ ] User profile editing (partially implemented in Mentor/Coordinator dashboards)
- [ ] Password change functionality
- [ ] Email notifications for status updates
- [ ] Bulk operations for coordinators (mentor assignment, status updates)

### **Duplicate Management UI - NOT STARTED**
- [ ] **Create `DuplicateReview.js` component** (access from all dashboards)
  - [ ] List all duplicate flags
  - [ ] Show side-by-side comparison of similar projects
  - [ ] Display similarity score (semantic + lexical breakdown)
  - [ ] Mark as reviewed button
  - [ ] Filter by reviewed status
- [ ] **Duplicate visualization**
  - [ ] Similarity score bar chart
  - [ ] Highlight matching text sections
  
### **Mentor Dashboard - NEEDS ENHANCEMENT**
- [x] Display list of mentees
- [ ] **Show mentees' projects**
  - [ ] List all projects by assigned students
  - [ ] Project status indicators
  - [ ] Quick stats (total, approved, pending)
- [ ] **Mentor actions**
  - [ ] Approve/reject project proposals
  - [ ] Flag/unflag duplicates
  - [ ] Leave feedback on projects
- [ ] **Appointment management**
  - [ ] View scheduled appointments
  - [ ] Confirm/cancel appointments

### **Coordinator Dashboard - SKELETON ONLY**
- [x] Dashboard layout exists with card buttons (no functionality)
- [ ] **Implement all coordinator functions:**
  - [ ] Manage Users page (create/edit/delete users, assign mentors)
  - [ ] System Reports page (statistics, charts)
  - [ ] Settings page (similarity thresholds, other config)
  - [ ] View All Projects page (with advanced filtering)
  - [ ] Duplicate Review page (admin-level duplicate management)
  - [ ] Bulk Operations page (mentor auto-assignment, data export)

### **Student Dashboard - NEEDS WORK**
- [x] Form to submit/edit project exists
- [ ] **Implement:**
  - [ ] View duplicate warnings if project flagged
  - [ ] Show project status (proposed/approved/rejected)
  - [ ] View mentor feedback/comments
  - [ ] Upload project documentation/files
- [ ] Better UX for form submission (progress indicator, success message)

---

## 🔴 Phase 5: Admin Features & Configuration (NOT STARTED)

### **Admin Dashboard Backend**
- [ ] Create `admin_dashboard` Django app (was mentioned in README but doesn't exist)
- [ ] Statistics/Analytics views:
  - [ ] Total projects by status
  - [ ] Duplicate detection rate
  - [ ] Mentor workload distribution
  - [ ] Project completion rates
- [ ] System configuration:
  - [ ] SIMILARITY_THRESHOLD setting (UI to adjust)
  - [ ] Batch operation schedule settings
  - [ ] Feature flags

### **Bulk Operations**
- [ ] **Mentor Auto-Assignment:**
  - [ ] Calculate mentor load (students per mentor)
  - [ ] Auto-assign new students to least-loaded mentors in their department
  - [ ] Manual reassignment UI
- [ ] **Data Export:**
  - [ ] CSV export of projects
  - [ ] CSV export of duplicate flags
  - [ ] Excel reports with statistics
- [ ] **Batch Email:**
  - [ ] Send notifications to users
  - [ ] Project status notifications

### **Advanced Duplicate Operations**
- [ ] **Merge Duplicates:** (Optional advanced feature)
  - [ ] Combine two projects into one
  - [ ] Handle project reassignment
  - [ ] Audit trail
- [ ] **Bulk Duplicate Check:** (Triggered periodically)
  - [ ] Management command to detect all duplicates
  - [ ] Email notifications of new flags

---

## 🔴 Phase 6: Testing & Deployment (NOT STARTED)

### **Unit Tests**
- [ ] Model tests (accounts.models, projects.models)
- [ ] API view tests (all CRUD endpoints)
- [ ] **Duplicate detection algorithm tests:**
  - [ ] Embedding generation tests
  - [ ] Similarity calculation tests (known pairs with expected scores)
  - [ ] Edge cases (empty text, very similar projects, identical projects)
- [ ] Serializer tests
- [ ] Permission/authentication tests

### **Integration Tests**
- [ ] End-to-end project submission workflow
- [ ] Duplicate detection workflow (create 2 similar projects → verify flagged)
- [ ] Frontend-backend integration (API response formats)
- [ ] User role-based access tests

### **Performance Testing**
- [ ] Benchmark embedding generation (target: < 1s per project)
- [ ] Test similarity search on large dataset (1000+ projects)
- [ ] Test batch duplicate detection performance
- [ ] Query optimization (index pgvector columns)

### **Deployment Setup**
- [ ] Docker setup (Dockerfile, docker-compose.yml)
- [ ] Environment variables configuration (.env template)
- [ ] Production settings (DEBUG=False, allowed hosts, secret key)
- [ ] Database migrations automation
- [ ] Static files collection
- [ ] CORS configuration for production domain
- [ ] SSL/HTTPS setup
- [ ] Gunicorn/uWSGI configuration
- [ ] Nginx reverse proxy setup
- [ ] PostgreSQL pgvector extension deployment

---

## 📋 Additional Issues & Fixes Needed

### **Backend Issues**
- [ ] API `/api/login/` uses session auth - consider JWT for better API usage (optional)
- [ ] No token refresh mechanism if using JWT
- [ ] No user registration endpoint (only admin can create users)
- [ ] ProjectSerializer doesn't include user info (creator name)
- [ ] Missing pagination on some endpoints
- [ ] Appointment model needs to be created and added to API

### **Frontend Issues**
- [ ] StudentDashboard form submission success handling (currently no feedback)
- [ ] Loading states inconsistent across components
- [ ] Error handling could be better (generic error messages)
- [ ] No form validation on frontend (only backend)
- [ ] MentorDashboard doesn't show projects - only mentees list
- [ ] CoordinatorDashboard has no actual functionality
- [ ] AuthContext checks `mentor_info` but serializer may not always include it

### **Database/Schema Issues**
- [ ] Verify pgvector extension exists: `CREATE EXTENSION IF NOT EXISTS vector;`
- [ ] pg_trgm extension needed for full-text search: `CREATE EXTENSION IF NOT EXISTS pg_trgm;`
- [ ] Create database indexes on frequently searched columns
- [ ] pgvector similarity search indexes: `CREATE INDEX ON projects USING ivfflat (combined_embedding vector_cosine_ops);`

### **DevOps/Infrastructure**
- [ ] requirements.txt may need updating (check version compatibility)
- [ ] venv/vee environment comparison complete (identical) - can remove vee if unused
  - [ ] Docker configuration
  - [ ] Production settings
  - [ ] Static file serving
  - [ ] Database migration scripts
  - [ ] Filter by mentor/student

---

## Phase 4: Mentor Assignment Logic
- [ ] **Automated Mentor Assignment**
  - [ ] Load balancing: assign to mentor with fewest students
  - [ ] Load balancing considering max_students limit
  - [ ] Assignment based on department/course
  - [ ] Manual override capability for admins

- [ ] **Mentor Assignment API**
  - [ ] Auto-assign endpoint
  - [ ] Manual assign endpoint
  - [ ] Reassign endpoint
  - [ ] Get available mentors endpoint

- [ ] **Mentor Availability**
  - [ ] Track mentor workload
  - [ ] Display mentor availability
  - [ ] Recommendations for student-mentor matching

---

## Phase 5: Notifications & Emails
- [ ] **Email Configuration**
  - [ ] Setup Django email backend (SMTP)
  - [ ] Create email templates for different events
  - [ ] Implement email sending utilities

- [ ] **Appointment Notifications**
  - [ ] Send confirmation email on appointment creation
  - [ ] Send reminder emails (24h, 1h before)
  - [ ] Send completion confirmation after appointment

- [ ] **Project Notifications**
  - [ ] Notify on duplicate detection
  - [ ] Notify on project approval/rejection
  - [ ] Notify mentor on new project assignment

- [ ] **Celery/Task Queue Setup** (optional)
  - [ ] Setup Celery + Redis for async tasks
  - [ ] Convert email sending to background tasks
  - [ ] Schedule periodic duplicate detection

---

## Phase 6: Frontend UI (React/Vue)
- [ ] **Project Management Dashboard**
  - [ ] List projects with filtering
  - [ ] Submit new project form
  - [ ] View project details
  - [ ] Search projects

- [ ] **Duplicate Detection UI**
  - [ ] View flagged duplicates
  - [ ] Mark as reviewed
  - [ ] Similarity score visualization

- [ ] **Appointment Calendar**
  - [ ] Calendar view of appointments
  - [ ] Schedule new appointment
  - [ ] Confirm/cancel appointments
  - [ ] Appointment details view

- [ ] **User Dashboard**
  - [ ] Personal project list
  - [ ] Upcoming appointments
  - [ ] Quick stats (total projects, pending reviews, etc.)

- [ ] **Admin Dashboard**
  - [ ] System statistics
  - [ ] User management
  - [ ] Configuration settings
  - [ ] Bulk operations

---

## Phase 7: Production Deployment
- [ ] **Environment Configuration**
  - [ ] Create .env.example file
  - [ ] Setup environment variables
  - [ ] Debug=False for production
  - [ ] SECRET_KEY rotation

- [ ] **Database Optimization**
  - [ ] Create database indexes for queries
  - [ ] Query optimization
  - [ ] Connection pooling setup

- [ ] **Security**
  - [ ] CSRF protection
  - [ ] CORS configuration for production domain
  - [ ] Rate limiting on API
  - [ ] Input validation & sanitization

- [ ] **Deployment**
  - [ ] Heroku/AWS/DigitalOcean setup
  - [ ] Gunicorn + Nginx configuration
  - [ ] SSL/TLS certificates
  - [ ] CI/CD pipeline (GitHub Actions)
  - [ ] Database migrations in production

- [ ] **Monitoring & Logging**
  - [ ] Setup error logging (Sentry)
  - [ ] Application performance monitoring
  - [ ] Log aggregation

---

## Phase 8: Testing & Documentation
- [ ] **Unit Tests**
  - [ ] Model tests
  - [ ] Serializer tests
  - [ ] View/API endpoint tests

- [ ] **Integration Tests**
  - [ ] End-to-end API workflows
  - [ ] Duplicate detection tests
  - [ ] Authentication tests

- [ ] **Documentation**
  - [ ] API documentation (Swagger/OpenAPI)
  - [ ] User guide
  - [ ] Developer setup guide
  - [ ] Deployment guide

---

## Notes
- Duplicate detection critical for project success
- Consider async task processing for embeddings
- Frontend framework: React recommended for flexibility
- Database backups critical for production
- Monitor performance as data grows
