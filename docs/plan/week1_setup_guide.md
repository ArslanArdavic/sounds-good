# Week 1 Setup Guide - Sounds Good

## ✅ Completed
- [x] Obtained Spotify Client ID & Secret
- [x] Obtained Groq API Key

## 🎯 Remaining Tasks

### 1. Repository & Environment Setup

#### 1.1 Initialize Git Repository
```bash
# Create project directory
mkdir sounds-good
cd sounds-good

# Initialize git
git init

# Create main branches
git checkout -b develop
git checkout -b main
git checkout develop  # Work on develop branch
```

#### 1.2 Create Project Structure
```bash
# Create directory structure
mkdir -p backend/{src,tests/{unit,integration,e2e},alembic}
mkdir -p frontend/{src,public}
mkdir -p docker
mkdir -p .github/workflows
mkdir -p docs/{api,architecture}
mkdir -p scripts

# Create subdirectories for backend
mkdir -p backend/src/{controllers,services,repositories,models,schemas,clients,utils,middleware}
mkdir -p backend/tests/{unit,integration,e2e}

# Create subdirectories for frontend
mkdir -p frontend/src/{components,pages,hooks,services,utils}
```

### 2. Backend Foundation

#### 2.1 Initialize Python Environment
```bash
cd backend

# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Initialize Poetry project
poetry init --name sounds-good-backend --python "^3.11"

# Add dependencies
poetry add fastapi uvicorn[standard] sqlalchemy alembic pydantic pydantic-settings
poetry add python-multipart python-jose[cryptography] passlib[bcrypt]
poetry add httpx chromadb sentence-transformers
poetry add cryptography python-dotenv redis

# Add development dependencies
poetry add --group dev pytest pytest-asyncio pytest-cov
poetry add --group dev ruff black mypy
poetry add --group dev pre-commit

# Install dependencies
poetry install

# Activate virtual environment (Poetry 2.x+)
source $(poetry env info --path)/bin/activate

# Or on Windows (PowerShell):
# & (poetry env info --path)/Scripts/Activate.ps1


#### 2.2 Create Backend Configuration Files

**pyproject.toml** (already created by poetry init, add these sections):
```toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.black]
line-length = 100
target-version = ['py311']

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = "test_*.py"
python_functions = "test_*"
addopts = "-v --cov=src --cov-report=term-missing"
```

#### 2.3 Set Up Database with Alembic
```bash
# Initialize Alembic
poetry run alembic init alembic

# This creates alembic.ini and alembic/ directory
```

### 3. Frontend Foundation

#### 3.1 Initialize React + Vite Project
```bash
cd ../frontend

# Create Vite project with React + TypeScript
npm create vite@latest . -- --template react-ts

# Install dependencies
npm install

# Install additional packages
npm install react-router-dom axios
npm install @tanstack/react-query
npm install -D tailwindcss postcss autoprefixer
npm install -D @types/node

# Install Tailwind v4 Vite plugin (replaces postcss/tailwind.config.js in v4)
npm install -D @tailwindcss/vite

# Install development dependencies
npm install -D eslint prettier eslint-config-prettier
npm install -D @typescript-eslint/eslint-plugin @typescript-eslint/parser
npm install -D @playwright/test
```

#### 3.2 Configure Tailwind CSS

> Tailwind v4 uses a Vite plugin — no `tailwind.config.js` or `postcss.config.js` needed.

Add the plugin to **vite.config.ts**:
```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
  ],
})
```

Replace **src/index.css** with:
```css
@import "tailwindcss";

@theme {
  --color-spotify-green: #1DB954;
}
```

### 4. Environment Configuration

#### 4.1 Backend Environment Variables

Create **backend/.env.example**:
```env
# Application
ENVIRONMENT=development
DEBUG=true
SECRET_KEY=your-secret-key-here
ENCRYPTION_KEY=your-encryption-key-here

# Database
DATABASE_URL=sqlite:///./sounds_good.db

# Redis (optional for development)
REDIS_URL=redis://localhost:6379

# ChromaDB
CHROMADB_HOST=localhost
CHROMADB_PORT=8000

# Spotify API
SPOTIFY_CLIENT_ID=your-spotify-client-id
SPOTIFY_CLIENT_SECRET=your-spotify-client-secret
SPOTIFY_REDIRECT_URI=http://localhost:3000/callback

# Groq API
GROQ_API_KEY=your-groq-api-key

# CORS
CORS_ORIGINS=http://localhost:3000
```

Create actual **backend/.env** with your real keys (this will be gitignored).

#### 4.2 Frontend Environment Variables

Create **frontend/.env.example**:
```env
VITE_API_URL=http://localhost:8000
VITE_SPOTIFY_CLIENT_ID=your-spotify-client-id
```

Create actual **frontend/.env** with your real values.

### 5. Git Configuration

#### 5.1 Create .gitignore

Create **root .gitignore**:
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg
MANIFEST
.pytest_cache/
.coverage
htmlcov/
*.cover
.hypothesis/

# Virtual environments
venv/
env/
ENV/
.venv

# Poetry
poetry.lock

# Environment variables
.env
.env.local
.env.*.local

# Database
*.db
*.sqlite
*.sqlite3

# ChromaDB
chroma_data/

# Node
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
pnpm-debug.log*
lerna-debug.log*
dist/
dist-ssr/
*.local

# Editor
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Docker
.dockerignore

# Logs
logs/
*.log
```

### 6. Pre-commit Hooks

Create **.pre-commit-config.yaml** in root:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.9
    hooks:
      - id: ruff
        args: [--fix]
        files: ^backend/

  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
        files: ^backend/

  - repo: https://github.com/pre-commit/mirrors-prettier
    rev: v3.1.0
    hooks:
      - id: prettier
        files: ^frontend/

  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: check-json
      - id: check-merge-conflict
```

Install hooks:
```bash
# From root directory
poetry run pre-commit install  # If you have poetry in root
# OR
pip install pre-commit
pre-commit install
```

### 7. Docker Configuration

Create **docker/Dockerfile.backend**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install Poetry
RUN pip install poetry

# Copy dependency files
COPY pyproject.toml poetry.lock ./

# Install dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

Create **docker/Dockerfile.frontend**:
```dockerfile
FROM node:18-alpine as build

WORKDIR /app

# Copy package files
COPY package*.json ./

# Install dependencies
RUN npm ci

# Copy source code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM nginx:alpine

# Copy built files
COPY --from=build /app/dist /usr/share/nginx/html

# Copy nginx config (to be created later)
# COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

Create **docker/docker-compose.yml**:
```yaml
version: '3.8'

services:
  backend:
    build:
      context: ../backend
      dockerfile: ../docker/Dockerfile.backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./sounds_good.db
    volumes:
      - ../backend:/app
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

  frontend:
    build:
      context: ../frontend
      dockerfile: ../docker/Dockerfile.frontend
    ports:
      - "3000:3000"
    environment:
      - VITE_API_URL=http://localhost:8000
    volumes:
      - ../frontend:/app
      - /app/node_modules
    command: npm run dev -- --host
```

### 8. Initial Commit

```bash
# From root directory
git add .
git commit -m "chore: initial project setup"
git push origin develop
```

## 📋 Checklist

- [ ] Git repository initialized
- [ ] Project structure created
- [ ] Poetry installed and configured
- [ ] Backend dependencies installed
- [ ] Alembic initialized
- [ ] Frontend Vite project created
- [ ] Tailwind CSS configured
- [ ] Environment files created (.env.example and .env)
- [ ] .gitignore created
- [ ] Pre-commit hooks installed
- [ ] Docker files created
- [ ] Initial commit pushed

## ⏭️ Next Steps

After completing these setup tasks, you're ready to move to the actual implementation:
1. Create FastAPI application structure
2. Set up database models
3. Implement health check endpoint
4. Create basic frontend layout

Would you like me to provide the implementation files for these next steps?
