# Sounds Good - Implementation Plan

## Table of Contents
1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [Development Phases](#development-phases)
5. [Testing Strategy](#testing-strategy)
6. [CI/CD Pipeline](#cicd-pipeline)
7. [Deployment Strategy](#deployment-strategy)
8. [Development Best Practices](#development-best-practices)
9. [Timeline & Milestones](#timeline--milestones)

---

## 1. Project Overview

**Application:** Sounds Good - AI-powered playlist generation from existing Spotify library  
**Architecture:** Monolithic FastAPI backend with SQLite + ChromaDB, React frontend  
**Key Features:** Spotify OAuth, RAG-based track retrieval, LLM playlist generation, vector search

### Success Criteria
- ✅ Authenticate users via Spotify OAuth
- ✅ Sync and cache 10,000+ tracks within 10 seconds
- ✅ Generate playlists within 30 seconds
- ✅ 100% track validation (all recommended tracks exist in user library)
- ✅ Duration matching within ±15 minute tolerance

---

## 2. Technology Stack

### Backend
- **Framework:** FastAPI 0.104+
- **Language:** Python 3.11+
- **ORM:** SQLAlchemy 2.0+
- **Database:** SQLite (development), PostgreSQL (production)
- **Vector Database:** ChromaDB 0.4+
- **Embeddings:** sentence-transformers (all-MiniLM-L6-v2)
- **LLM API:** Groq (Llama 3.1 70B)
- **HTTP Client:** httpx (async)
- **Validation:** Pydantic V2
- **Security:** cryptography (Fernet for token encryption)

### Frontend
- **Framework:** React 18+
- **Build Tool:** Vite
- **State Management:** React Query + Context API
- **Styling:** Tailwind CSS
- **HTTP Client:** Axios
- **Auth:** OAuth 2.0 PKCE flow

### External APIs
- Spotify Web API v1
- Groq API (LLM inference)

### Development Tools
- **Package Manager:** Poetry (Python), npm (JavaScript)
- **Linting:** Ruff (Python), ESLint (JavaScript)
- **Formatting:** Black (Python), Prettier (JavaScript)
- **Type Checking:** Mypy (Python), TypeScript
- **Testing:** pytest, pytest-asyncio, React Testing Library
- **API Documentation:** FastAPI auto-generated Swagger/OpenAPI

---

## 3. Project Structure

```
sounds-good/
├── backend/
│   ├── src/
│   │   ├── __init__.py
│   │   ├── main.py                      # FastAPI app entry point
│   │   ├── config.py                    # Configuration management
│   │   ├── controllers/
│   │   │   ├── __init__.py
│   │   │   ├── auth_controller.py
│   │   │   ├── playlist_controller.py
│   │   │   └── user_controller.py
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── spotify_auth_service.py
│   │   │   ├── spotify_service.py
│   │   │   ├── llm_service.py
│   │   │   ├── embedding_service.py
│   │   │   ├── playlist_generation_service.py
│   │   │   └── vector_search_service.py
│   │   ├── repositories/
│   │   │   ├── __init__.py
│   │   │   ├── user_repository.py
│   │   │   ├── track_repository.py
│   │   │   ├── playlist_repository.py
│   │   │   └── token_repository.py
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── database.py              # SQLAlchemy setup
│   │   │   ├── user.py
│   │   │   ├── track.py
│   │   │   ├── playlist.py
│   │   │   └── spotify_token.py
│   │   ├── schemas/                      # Pydantic models
│   │   │   ├── __init__.py
│   │   │   ├── user_schema.py
│   │   │   ├── track_schema.py
│   │   │   ├── playlist_schema.py
│   │   │   └── request_schema.py
│   │   ├── clients/
│   │   │   ├── __init__.py
│   │   │   ├── spotify_client.py
│   │   │   ├── llm_client.py
│   │   │   └── chromadb_client.py
│   │   ├── utils/
│   │   │   ├── __init__.py
│   │   │   ├── prompt_builder.py
│   │   │   ├── track_validator.py
│   │   │   ├── duration_matcher.py
│   │   │   └── token_encryptor.py
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── error_handler.py
│   │       └── auth_middleware.py
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── alembic/                          # Database migrations
│   ├── pyproject.toml
│   ├── poetry.lock
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── services/
│   │   ├── utils/
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/
│   ├── package.json
│   ├── vite.config.ts
│   └── tsconfig.json
├── .github/
│   └── workflows/
│       ├── backend-ci.yml
│       ├── frontend-ci.yml
│       └── deploy.yml
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
├── docs/
│   ├── api/
│   └── architecture/
├── scripts/
│   ├── setup.sh
│   └── seed_data.sh
├── .gitignore
├── README.md
└── LICENSE
```

---

## 4. Development Phases

### Phase 0: Project Setup (Week 1)
**Goal:** Establish development environment and project foundation

#### Tasks:
1. **Repository & Environment Setup**
   - Initialize Git repository
   - Set up branch protection rules (main, develop)
   - Configure Python 3.11+ virtual environment with Poetry
   - Configure Node.js 18+ with npm
   - Create `.env.example` files for both backend and frontend
   - Set up pre-commit hooks (Ruff, Black, ESLint, Prettier)

2. **Backend Foundation**
   - Initialize FastAPI project structure
   - Configure SQLAlchemy with SQLite (dev) and Alembic for migrations
   - Set up dependency injection container
   - Configure CORS middleware
   - Implement health check endpoint (`/health`)
   - Create initial database schema migration

3. **Frontend Foundation**
   - Initialize React + Vite project
   - Set up Tailwind CSS
   - Configure routing (React Router)
   - Create basic layout components
   - Set up environment variable management

4. **External Service Accounts**
   - Register Spotify Developer application
   - Create Groq API account and obtain API key
   - Set up OAuth redirect URIs

**Deliverables:**
- Working dev environment with hot reload
- Database migrations framework
- Basic health check endpoint
- Frontend boilerplate with routing

---

### Phase 1: Authentication & User Management (Week 2)
**Goal:** Implement Spotify OAuth and user session management

#### Backend Tasks:
1. **Spotify OAuth Flow**
   - Implement `AuthController` with `/login` and `/callback` endpoints
   - Develop `SpotifyAuthService`:
     - Generate authorization URL with PKCE
     - Exchange authorization code for tokens
     - Refresh token mechanism
   - Create `SpotifyClient` for API communication
   - Implement `TokenEncryptor` using Fernet encryption
   - Build `TokenRepository` for encrypted token storage
   - Create `UserRepository` and `User` model

2. **Session Management**
   - Implement JWT-based session tokens
   - Create authentication middleware
   - Add user context injection for authenticated routes

3. **Error Handling**
   - OAuth failure scenarios (denied permissions, invalid code)
   - Token refresh failures
   - Global error handler middleware

#### Frontend Tasks:
1. **Authentication UI**
   - Welcome screen with "Connect with Spotify" button
   - OAuth callback handler
   - Loading states during authentication
   - Error display for auth failures

2. **Session Management**
   - Store JWT in httpOnly cookies or localStorage
   - Implement protected route wrapper
   - Auto-redirect to login for unauthenticated users

**Testing:**
- Unit tests for token encryption/decryption
- Integration tests for OAuth flow
- E2E test for complete authentication journey

**Acceptance Criteria:**
- ✅ User can authenticate via Spotify OAuth
- ✅ Tokens are encrypted and securely stored
- ✅ Session persists across page refreshes
- ✅ Token refresh works automatically

---

### Phase 2: Library Sync & Track Storage (Week 3)
**Goal:** Fetch, store, and index user's Spotify library

#### Backend Tasks:
1. **Spotify Data Retrieval**
   - Implement `SpotifyService`:
     - `get_user_playlists()` with pagination
     - `get_playlist_tracks()` with pagination
     - `get_audio_features()` in batches of 100
   - Handle Spotify API rate limits (retry with exponential backoff)
   - Implement progress tracking for sync operations

2. **Track Storage**
   - Create `Track`, `Playlist`, `PlaylistTrack` models
   - Implement `TrackRepository.bulk_create()` for efficient inserts
   - Add 24-hour cache expiration logic (delete old tracks)
   - Create database indexes on `user_id`, `spotify_track_id`

3. **Vector Embedding & Indexing**
   - Implement `EmbeddingService`:
     - Load sentence-transformers model (all-MiniLM-L6-v2)
     - Generate embeddings from track metadata
     - Batch processing for performance
   - Develop `VectorSearchService`:
     - Initialize ChromaDB collection per user
     - Add embeddings with metadata
     - Implement `clear_user_tracks()` for re-sync
   - Create `ChromaDBClient` wrapper

4. **Background Jobs**
   - Implement async library sync with progress updates
   - Add WebSocket endpoint for real-time sync status
   - Handle partial sync failures (retry mechanisms)

#### Frontend Tasks:
1. **Library Sync UI**
   - Syncing screen with progress indicators
   - Display: "X/50 playlists found, Y tracks processed"
   - Progress bar visualization
   - Success screen: "5,000 tracks from 50 playlists ready"
   - Handle sync errors with retry option

2. **WebSocket Integration**
   - Connect to sync status endpoint
   - Update UI in real-time during sync

**Testing:**
- Mock Spotify API responses for different scenarios
- Test bulk insert performance (10,000 tracks)
- Verify ChromaDB indexing correctness
- Test 24-hour cache expiration logic
- Load test with 10,000+ tracks

**Acceptance Criteria:**
- ✅ System retrieves all playlists and tracks from Spotify
- ✅ Sync completes within 10 seconds for 10,000 tracks
- ✅ Embeddings are generated and indexed correctly
- ✅ Progress is displayed in real-time
- ✅ Cache expiration works after 24 hours

---

### Phase 3: RAG Pipeline & Vector Search (Week 4)
**Goal:** Implement semantic search to retrieve relevant tracks

#### Backend Tasks:
1. **Query Embedding**
   - Extend `EmbeddingService.encode_query()`
   - Handle various query formats and lengths
   - Optimize embedding generation latency

2. **Vector Search Implementation**
   - Implement `VectorSearchService.search()`:
     - Perform similarity search in ChromaDB
     - Return top N results (configurable, default 1000)
     - Include metadata in results
   - Fine-tune similarity thresholds
   - Implement result reranking if needed

3. **Track Retrieval**
   - Develop `PlaylistGenerationService.retrieve_tracks()`:
     - Encode user query
     - Perform vector search
     - Fetch full track details from database
     - Filter by audio features if specified

**Testing:**
- Test semantic similarity (e.g., "upbeat dance" vs "energetic workout")
- Verify retrieval quality with diverse queries
- Benchmark search latency (<1 second for 10,000 tracks)
- Test edge cases (empty library, single track, etc.)

**Acceptance Criteria:**
- ✅ Query embedding is fast (<100ms)
- ✅ Vector search returns semantically relevant tracks
- ✅ Top 500-1000 tracks retrieved based on query
- ✅ Search latency is under 1 second

---

### Phase 4: LLM Integration & Playlist Generation (Week 5)
**Goal:** Generate playlists using LLM with retrieved tracks

#### Backend Tasks:
1. **Prompt Engineering**
   - Implement `PromptBuilder`:
     - Format user request
     - Include retrieved tracks with metadata
     - Add system instructions (duration, validation)
     - Optimize prompt length (stay within token limits)
   - Create prompt templates for different scenarios

2. **LLM Service**
   - Develop `LLMClient` for Groq API
   - Implement `LLMService.generate()`:
     - Send prompt to Llama 3.1 70B
     - Parse JSON response
     - Handle API errors and timeouts
   - Add retry logic with exponential backoff
   - Implement response validation

3. **Track Validation**
   - Create `TrackValidator`:
     - Verify all track IDs exist in user library
     - Identify invalid tracks
     - Generate feedback for LLM retry
   - Implement validation error handling

4. **Duration Matching**
   - Develop `DurationMatcher`:
     - Calculate total playlist duration
     - Check against target ±15 min tolerance
     - Generate feedback for LLM adjustment

5. **Orchestration**
   - Complete `PlaylistGenerationService`:
     - Coordinate RAG retrieval
     - Build and send LLM prompt
     - Validate response
     - Retry with feedback if needed (max 3 attempts)
     - Create playlist record

#### Frontend Tasks:
1. **Playlist Request UI**
   - Input form with textarea
   - "Generate Playlist" button
   - Loading state with spinner
   - Example prompts ("Try these")

2. **Result Display**
   - Playlist header (name, duration, track count)
   - Scrollable track list with:
     - Track number
     - Track name
     - Artist name
     - Duration
   - "Save to Spotify" button
   - "Generate another" button

**Testing:**
- Unit tests for prompt building
- Mock LLM responses for different scenarios
- Test validation with invalid track IDs
- Test duration matching logic
- Integration test for full generation flow
- Test retry mechanism

**Acceptance Criteria:**
- ✅ LLM generates playlists within 30 seconds
- ✅ All recommended tracks exist in user library
- ✅ Duration is within ±15 minute tolerance
- ✅ Retry mechanism works for invalid responses
- ✅ UI displays results correctly

---

### Phase 5: Spotify Playlist Creation (Week 6)
**Goal:** Save generated playlists to user's Spotify account

#### Backend Tasks:
1. **Spotify Playlist API**
   - Extend `SpotifyService`:
     - `create_playlist(user_id, name, description)`
     - `add_tracks_to_playlist(playlist_id, track_uris)` in batches
   - Handle API errors and rate limits

2. **Playlist Persistence**
   - Extend `PlaylistRepository`:
     - Link local playlist to Spotify playlist ID
     - Track sync status

#### Frontend Tasks:
1. **Save Functionality**
   - "Save to Spotify" button handler
   - Loading state during save
   - Success confirmation
   - Error handling with retry option

**Testing:**
- Test playlist creation with various track counts
- Test batching for large playlists (100+ tracks)
- Mock Spotify API for different error scenarios

**Acceptance Criteria:**
- ✅ Playlists are created in user's Spotify account
- ✅ All tracks are added successfully
- ✅ User receives confirmation

---

### Phase 6: Performance Optimization & Caching (Week 7)
**Goal:** Optimize system performance and reduce latency

#### Tasks:
1. **Database Optimization**
   - Add composite indexes for common queries
   - Implement connection pooling
   - Optimize bulk insert operations
   - Add database query logging and analysis

2. **Caching Strategy**
   - Implement Redis for:
     - User session cache
     - Frequently accessed track metadata
     - LLM response cache (for identical queries)
   - Set appropriate TTLs

3. **API Response Caching**
   - Cache Spotify API responses for:
     - User playlists (1 hour)
     - Audio features (24 hours)
   - Implement cache invalidation logic

4. **Async Operations**
   - Convert blocking operations to async
   - Use connection pooling for httpx
   - Implement background task queue (Celery or FastAPI BackgroundTasks)

5. **Frontend Optimization**
   - Implement React Query for data caching
   - Add optimistic UI updates
   - Lazy load components
   - Optimize bundle size

**Testing:**
- Load testing with 100 concurrent users
- Measure sync time for 10,000 tracks
- Benchmark playlist generation latency
- Monitor memory usage during operations

**Acceptance Criteria:**
- ✅ Library sync completes in <10 seconds for 10,000 tracks
- ✅ Playlist generation completes in <30 seconds
- ✅ Application handles 100 concurrent users
- ✅ API response times are <200ms (excluding LLM calls)

---

### Phase 7: Error Handling & User Experience (Week 8)
**Goal:** Implement comprehensive error handling and improve UX

#### Backend Tasks:
1. **Robust Error Handling**
   - Create custom exception hierarchy
   - Implement global exception handler
   - Add detailed error logging
   - Return user-friendly error messages

2. **Input Validation**
   - Validate all user inputs with Pydantic
   - Sanitize natural language queries
   - Implement rate limiting per user

3. **Monitoring & Logging**
   - Set up structured logging (JSON format)
   - Add request/response logging
   - Implement performance monitoring
   - Track key metrics (sync time, generation time, success rate)

#### Frontend Tasks:
1. **Error Handling**
   - Display user-friendly error messages
   - Add retry buttons for recoverable errors
   - Show fallback UI for failed operations

2. **Loading States**
   - Skeleton screens for loading content
   - Progress indicators for long operations
   - Optimistic updates where appropriate

3. **User Feedback**
   - Success/error toast notifications
   - Clear status messages
   - Help text and tooltips

**Testing:**
- Test all error scenarios
- Verify error messages are helpful
- Test retry mechanisms
- User acceptance testing

**Acceptance Criteria:**
- ✅ All errors are handled gracefully
- ✅ User receives clear feedback
- ✅ Application doesn't crash on errors
- ✅ Logs provide debugging information

---

### Phase 8: Security Hardening (Week 9)
**Goal:** Ensure application security and data protection

#### Tasks:
1. **Authentication & Authorization**
   - Implement CSRF protection
   - Add rate limiting on auth endpoints
   - Secure session management
   - Implement token rotation

2. **Data Protection**
   - Encrypt sensitive data at rest
   - Use HTTPS in production
   - Implement secure headers (HSTS, CSP, etc.)
   - Sanitize all user inputs

3. **API Security**
   - Validate all API requests
   - Implement request signing
   - Add API key rotation mechanism
   - Protect against common attacks (SQL injection, XSS, CSRF)

4. **Dependency Security**
   - Run security audits on dependencies
   - Set up automated vulnerability scanning
   - Keep dependencies up to date

5. **Compliance**
   - Ensure GDPR compliance (data deletion, export)
   - Implement privacy policy
   - Add terms of service
   - User consent management

**Testing:**
- Security penetration testing
- Dependency vulnerability scanning
- OWASP Top 10 checklist
- API security testing

**Acceptance Criteria:**
- ✅ No critical security vulnerabilities
- ✅ Sensitive data is encrypted
- ✅ HTTPS enforced in production
- ✅ Rate limiting prevents abuse

---

## 5. Testing Strategy

### Unit Testing
**Coverage Target:** 80%+

#### Backend (pytest)
- All services with mocked dependencies
- Repository methods with in-memory database
- Utility functions (validation, encryption, etc.)
- Client wrappers with mocked HTTP responses

#### Frontend (React Testing Library)
- Component rendering and behavior
- Hooks functionality
- Utility functions
- State management

### Integration Testing
**Coverage:** Critical paths

#### Backend
- API endpoint tests with TestClient
- Database operations with test database
- External API integration with mocks
- Service layer integration

#### Frontend
- Component integration with mocked API
- User flows (auth, sync, generation)
- Form submissions and validations

### End-to-End Testing
**Tool:** Playwright or Cypress

#### Critical User Journeys:
1. Complete authentication flow
2. Library sync process
3. Playlist generation and save
4. Error recovery scenarios

### Performance Testing
**Tool:** Locust or k6

#### Scenarios:
- Concurrent user authentication
- Simultaneous library syncs
- Multiple playlist generation requests
- API response time under load

### Security Testing
**Tools:** OWASP ZAP, Bandit, npm audit

#### Tests:
- Authentication bypass attempts
- SQL injection attempts
- XSS vulnerability scanning
- Dependency vulnerability scanning
- API rate limit testing

---

## 6. CI/CD Pipeline

### Continuous Integration

#### GitHub Actions Workflows

**1. Backend CI (`.github/workflows/backend-ci.yml`)**
Triggers: Push to main/develop, Pull requests

```yaml
name: Backend CI

on:
  push:
    branches: [main, develop]
    paths:
      - 'backend/**'
  pull_request:
    branches: [main, develop]
    paths:
      - 'backend/**'

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.11', '3.12']
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}
      
      - name: Install Poetry
        run: |
          curl -sSL https://install.python-poetry.org | python3 -
          echo "$HOME/.local/bin" >> $GITHUB_PATH
      
      - name: Install dependencies
        working-directory: ./backend
        run: poetry install
      
      - name: Run Ruff linter
        working-directory: ./backend
        run: poetry run ruff check .
      
      - name: Run Black formatter check
        working-directory: ./backend
        run: poetry run black --check .
      
      - name: Run Mypy type checker
        working-directory: ./backend
        run: poetry run mypy src/
      
      - name: Run tests with coverage
        working-directory: ./backend
        run: |
          poetry run pytest tests/ \
            --cov=src \
            --cov-report=xml \
            --cov-report=term-missing
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml
          flags: backend
      
      - name: Security scan with Bandit
        working-directory: ./backend
        run: poetry run bandit -r src/

  build:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Build Docker image
        run: |
          docker build \
            -f docker/Dockerfile.backend \
            -t sounds-good-backend:${{ github.sha }} \
            ./backend
```

**2. Frontend CI (`.github/workflows/frontend-ci.yml`)**
Triggers: Push to main/develop, Pull requests

```yaml
name: Frontend CI

on:
  push:
    branches: [main, develop]
    paths:
      - 'frontend/**'
  pull_request:
    branches: [main, develop]
    paths:
      - 'frontend/**'

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        node-version: ['18.x', '20.x']
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: ${{ matrix.node-version }}
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci
      
      - name: Run ESLint
        working-directory: ./frontend
        run: npm run lint
      
      - name: Run Prettier check
        working-directory: ./frontend
        run: npm run format:check
      
      - name: Type check
        working-directory: ./frontend
        run: npm run type-check
      
      - name: Run tests
        working-directory: ./frontend
        run: npm run test:coverage
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          files: ./frontend/coverage/coverage-final.json
          flags: frontend
      
      - name: Build application
        working-directory: ./frontend
        run: npm run build
      
      - name: Security audit
        working-directory: ./frontend
        run: npm audit --audit-level=high

  e2e:
    runs-on: ubuntu-latest
    needs: test
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20.x'
      
      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci
      
      - name: Install Playwright
        working-directory: ./frontend
        run: npx playwright install --with-deps
      
      - name: Run E2E tests
        working-directory: ./frontend
        run: npm run test:e2e
      
      - name: Upload Playwright report
        if: failure()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: frontend/playwright-report/
```

**3. Deployment Workflow (`.github/workflows/deploy.yml`)**
Triggers: Push to main (production), Push to develop (staging)

```yaml
name: Deploy

on:
  push:
    branches:
      - main      # Production
      - develop   # Staging

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: ${{ github.ref == 'refs/heads/main' && 'production' || 'staging' }}
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set environment variables
        run: |
          if [[ "${{ github.ref }}" == "refs/heads/main" ]]; then
            echo "ENVIRONMENT=production" >> $GITHUB_ENV
            echo "DEPLOY_URL=${{ secrets.PROD_DEPLOY_URL }}" >> $GITHUB_ENV
          else
            echo "ENVIRONMENT=staging" >> $GITHUB_ENV
            echo "DEPLOY_URL=${{ secrets.STAGING_DEPLOY_URL }}" >> $GITHUB_ENV
          fi
      
      - name: Build and push Docker images
        run: |
          echo "${{ secrets.DOCKER_PASSWORD }}" | docker login -u "${{ secrets.DOCKER_USERNAME }}" --password-stdin
          
          docker build -f docker/Dockerfile.backend -t ${{ secrets.DOCKER_REGISTRY }}/sounds-good-backend:${{ env.ENVIRONMENT }}-${{ github.sha }} ./backend
          docker push ${{ secrets.DOCKER_REGISTRY }}/sounds-good-backend:${{ env.ENVIRONMENT }}-${{ github.sha }}
          
          docker build -f docker/Dockerfile.frontend -t ${{ secrets.DOCKER_REGISTRY }}/sounds-good-frontend:${{ env.ENVIRONMENT }}-${{ github.sha }} ./frontend
          docker push ${{ secrets.DOCKER_REGISTRY }}/sounds-good-frontend:${{ env.ENVIRONMENT }}-${{ github.sha }}
      
      - name: Deploy to server
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.DEPLOY_HOST }}
          username: ${{ secrets.DEPLOY_USER }}
          key: ${{ secrets.DEPLOY_SSH_KEY }}
          script: |
            cd /opt/sounds-good
            docker-compose pull
            docker-compose up -d
            docker system prune -af
      
      - name: Run database migrations
        run: |
          ssh ${{ secrets.DEPLOY_USER }}@${{ secrets.DEPLOY_HOST }} \
            "cd /opt/sounds-good && docker-compose exec backend poetry run alembic upgrade head"
      
      - name: Health check
        run: |
          sleep 10
          curl -f ${{ env.DEPLOY_URL }}/health || exit 1
      
      - name: Notify deployment
        if: success()
        uses: 8398a7/action-slack@v3
        with:
          status: custom
          custom_payload: |
            {
              text: "✅ Deployment to ${{ env.ENVIRONMENT }} successful",
              attachments: [{
                color: 'good',
                text: `Commit: ${{ github.sha }}\nAuthor: ${{ github.actor }}\nBranch: ${{ github.ref }}`
              }]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
```

### Branch Strategy
- **main:** Production-ready code
- **develop:** Integration branch for features
- **feature/*:** Individual feature branches
- **hotfix/*:** Emergency production fixes

### Pull Request Requirements
- ✅ All CI checks pass
- ✅ Code review approval (minimum 1 reviewer)
- ✅ Test coverage doesn't decrease
- ✅ No security vulnerabilities introduced
- ✅ Documentation updated if needed

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix]
  
  - repo: https://github.com/psf/black
    rev: 23.10.0
    hooks:
      - id: black
  
  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.0.3
    hooks:
      - id: prettier
        files: \.(js|jsx|ts|tsx|json|css|md)$
  
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
```

---

## 7. Deployment Strategy

### Infrastructure

#### Option 1: Docker Compose (Simple Deployment)
**Best for:** Small-scale deployment, staging environments

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: ../docker/Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/sounds_good
      - REDIS_URL=redis://redis:6379
      - CHROMADB_HOST=chromadb
      - SPOTIFY_CLIENT_ID=${SPOTIFY_CLIENT_ID}
      - SPOTIFY_CLIENT_SECRET=${SPOTIFY_CLIENT_SECRET}
      - GROQ_API_KEY=${GROQ_API_KEY}
      - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    depends_on:
      - db
      - redis
      - chromadb
    volumes:
      - ./backend:/app
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000

  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    depends_on:
      - backend

  db:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=sounds_good
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD}

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chromadb_data:/chroma/chroma
    environment:
      - CHROMA_SERVER_AUTH_CREDENTIALS=${CHROMA_AUTH}

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - frontend
      - backend

volumes:
  postgres_data:
  redis_data:
  chromadb_data:
```

#### Option 2: Kubernetes (Scalable Production)
**Best for:** Production with auto-scaling, high availability

**Key resources:**
- Deployments for backend, frontend, ChromaDB
- Services (LoadBalancer/ClusterIP)
- Ingress for routing
- ConfigMaps for configuration
- Secrets for sensitive data
- Persistent Volumes for database
- HorizontalPodAutoscaler for auto-scaling

#### Option 3: Serverless (Cloud-Native)
**Best for:** Cost optimization, variable load

- Backend: AWS Lambda + API Gateway or Google Cloud Run
- Frontend: Vercel or Netlify
- Database: AWS RDS (PostgreSQL) or Google Cloud SQL
- Vector DB: Pinecone (managed ChromaDB alternative)
- Cache: AWS ElastiCache (Redis)

### Environment Configuration

**Development:**
- SQLite database
- Local ChromaDB
- No Redis (in-memory cache)
- Debug logging enabled
- CORS allow all origins

**Staging:**
- PostgreSQL database
- Dedicated ChromaDB instance
- Redis cache
- Info logging
- CORS restricted to staging domain

**Production:**
- PostgreSQL with replication
- ChromaDB with backups
- Redis cluster
- Error/warning logging only
- CORS restricted to production domain
- HTTPS enforced
- Rate limiting enabled

### Monitoring & Observability

**Application Monitoring:**
- **Tool:** Prometheus + Grafana or Datadog
- **Metrics:**
  - Request rate, latency, error rate
  - Library sync time
  - Playlist generation time
  - Database query performance
  - ChromaDB search latency
  - LLM API latency and errors

**Logging:**
- **Tool:** ELK Stack (Elasticsearch, Logstash, Kibana) or Cloud provider logging
- **Log levels:** ERROR, WARNING, INFO, DEBUG
- **Structured logging:** JSON format with context

**Alerts:**
- High error rate (>5%)
- Slow response times (>2s for API, >40s for generation)
- Database connection failures
- External API failures (Spotify, Groq)
- Disk space low
- Memory usage high

**Uptime Monitoring:**
- **Tool:** UptimeRobot or Pingdom
- Monitor `/health` endpoint
- Alert on downtime >1 minute

### Backup Strategy

**Database Backups:**
- Automated daily backups
- Retain 30 days of backups
- Test restoration monthly

**ChromaDB Backups:**
- Weekly full backups
- Retain 4 weeks of backups

**Configuration Backups:**
- Version control for all config
- Encrypted secrets in password manager
- Document restoration procedures

---

## 8. Development Best Practices

### Code Quality Standards

**Python (Backend):**
- Follow PEP 8 style guide
- Use type hints for all functions
- Docstrings for all public methods (Google style)
- Max line length: 100 characters
- Max function complexity: 10 (cyclomatic complexity)

**TypeScript/JavaScript (Frontend):**
- Follow Airbnb style guide
- Use TypeScript strict mode
- Document complex components with JSDoc
- Max file length: 300 lines
- Prefer functional components and hooks

### Git Commit Conventions

**Format:** `<type>(<scope>): <subject>`

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(auth): implement Spotify OAuth flow
fix(playlist): correct duration calculation tolerance
docs(api): update authentication endpoints
test(services): add unit tests for LLMService
```

### Code Review Checklist

**Functionality:**
- ✅ Code works as intended
- ✅ Edge cases are handled
- ✅ Error handling is appropriate
- ✅ No breaking changes without migration plan

**Code Quality:**
- ✅ Code is readable and maintainable
- ✅ No code duplication
- ✅ Functions are single-purpose
- ✅ Variable/function names are descriptive
- ✅ Comments explain "why," not "what"

**Testing:**
- ✅ Unit tests cover new code
- ✅ Integration tests for new features
- ✅ Tests are deterministic
- ✅ Test coverage doesn't decrease

**Security:**
- ✅ No sensitive data in code
- ✅ User input is validated
- ✅ Authentication/authorization is correct
- ✅ No new security vulnerabilities

**Performance:**
- ✅ No N+1 queries
- ✅ Appropriate use of caching
- ✅ Database queries are optimized
- ✅ No memory leaks

### Documentation Standards

**Required Documentation:**
1. **README.md:**
   - Project overview
   - Setup instructions
   - Development workflow
   - Deployment guide

2. **API Documentation:**
   - OpenAPI/Swagger auto-generated docs
   - Example requests/responses
   - Authentication requirements
   - Rate limits

3. **Architecture Documentation:**
   - System architecture diagram
   - Data flow diagrams
   - Database schema
   - External dependencies

4. **Runbooks:**
   - Deployment procedures
   - Rollback procedures
   - Troubleshooting common issues
   - Incident response plan

### Security Best Practices

**Development:**
- Never commit secrets to version control
- Use environment variables for configuration
- Rotate API keys regularly
- Run security scans in CI/CD

**Production:**
- Use HTTPS everywhere
- Implement rate limiting
- Sanitize all user inputs
- Encrypt sensitive data at rest
- Use secure session management
- Keep dependencies updated
- Follow principle of least privilege

### Performance Best Practices

**Backend:**
- Use database indexes strategically
- Implement connection pooling
- Cache frequently accessed data
- Use async operations for I/O
- Batch external API calls
- Monitor query performance

**Frontend:**
- Code splitting for large bundles
- Lazy load components
- Optimize images
- Use React.memo for expensive components
- Debounce user inputs
- Implement virtual scrolling for large lists

---

## 9. Timeline & Milestones

### Development Timeline (9 weeks)

| Week | Phase | Key Deliverables |
|------|-------|------------------|
| 1 | Phase 0: Setup | Dev environment, basic structure, health endpoint |
| 2 | Phase 1: Auth | Spotify OAuth, user sessions, JWT |
| 3 | Phase 2: Library Sync | Spotify data retrieval, track storage, embeddings |
| 4 | Phase 3: RAG | Vector search, track retrieval |
| 5 | Phase 4: LLM | Prompt engineering, playlist generation |
| 6 | Phase 5: Spotify Save | Playlist creation in Spotify |
| 7 | Phase 6: Optimization | Performance tuning, caching |
| 8 | Phase 7: UX | Error handling, loading states |
| 9 | Phase 8: Security | Security hardening, compliance |

### Release Milestones

**Alpha Release (Week 5):** 
- Core functionality complete
- Internal testing only
- Basic error handling
- No performance optimization

**Beta Release (Week 7):**
- All features implemented
- Performance optimized
- External beta testers invited
- Monitoring in place

**Production Release (Week 10):**
- Security hardened
- Full documentation
- CI/CD pipeline complete
- Monitoring and alerts configured

### Post-Launch Roadmap

**Version 1.1 (Month 2):**
- User feedback incorporation
- Performance improvements
- Bug fixes

**Version 1.2 (Month 3):**
- Advanced filtering options
- Playlist collaboration features
- Mood-based automatic playlist updates

**Version 2.0 (Month 6):**
- Multi-platform support (Apple Music, YouTube Music)
- Social features (share playlists)
- Mobile app (React Native)
- Advanced analytics dashboard

---

## Success Metrics

### Technical Metrics
- Library sync time: <10s for 10,000 tracks
- Playlist generation: <30s
- API uptime: >99.9%
- Test coverage: >80%
- Zero critical security vulnerabilities

### Business Metrics
- User authentication success rate: >95%
- Playlist generation success rate: >90%
- User retention (7-day): >40%
- Average playlists per user: >3
- User satisfaction (NPS): >50

---

## Risk Management

### Technical Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Spotify API rate limits | High | Medium | Implement exponential backoff, request batching |
| LLM API failures | High | Low | Retry logic, fallback to rule-based selection |
| ChromaDB performance issues | Medium | Low | Optimize embeddings, implement caching |
| Token encryption vulnerabilities | Critical | Low | Regular security audits, key rotation |
| Database scalability | High | Medium | PostgreSQL with proper indexing, consider sharding |

### Business Risks

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| Spotify API ToS violation | Critical | Low | Careful review of ToS, legal consultation |
| LLM costs exceed budget | Medium | Medium | Implement request caching, usage monitoring |
| User privacy concerns | High | Medium | Clear privacy policy, GDPR compliance |
| Low user adoption | High | Medium | User testing, iterate on UX |

---

## Appendix

### Required API Keys & Credentials
- Spotify Client ID & Secret
- Groq API Key
- Encryption key (generate with `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`)
- JWT secret key
- Database credentials
- Redis credentials (production)

### Development Tools Checklist
- [ ] Python 3.11+
- [ ] Node.js 18+
- [ ] Poetry
- [ ] Docker & Docker Compose
- [ ] Git
- [ ] VS Code or PyCharm
- [ ] Postman or Insomnia (API testing)
- [ ] PostgreSQL client

### Useful Resources
- [Spotify Web API Documentation](https://developer.spotify.com/documentation/web-api)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Groq API Documentation](https://console.groq.com/docs)
- [sentence-transformers Documentation](https://www.sbert.net/)

---

**Document Version:** 1.0  
**Last Updated:** 2024-03-19  
**Maintained By:** Development Team
