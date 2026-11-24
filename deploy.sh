#!/bin/bash
# deploy.sh - Deploy OmniMigrate to production
# Usage: ./deploy.sh [vercel|render|vps]

set -e

DEPLOY_TARGET=${1:-vercel}

echo "🚀 Deploying OmniMigrate to $DEPLOY_TARGET..."

# Build and test first
echo "📦 Running CI checks..."
cd backend
# The project targets Python 3.12; 3.14 cannot build some pinned wheels.
PYTHON_BIN=${PYTHON_BIN:-python3.12}
$PYTHON_BIN -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
ruff check app tests
ruff format --check app tests
pyright app
pytest tests/ -q --tb=short --cov=app --cov-fail-under=65
deactivate
cd ..

cd frontend
npm ci
npx tsc --noEmit
npm test
npm run build
cd ..

if [ "$DEPLOY_TARGET" = "vercel" ]; then
    echo "🚀 Deploying to Vercel + Render..."

    # Frontend to Vercel
    echo "📦 Deploying frontend to Vercel..."
    npx vercel --prod --yes

    echo "✅ Frontend deployed to Vercel"
    echo "🔧 Configure Render backend separately via render.yaml"
    echo "📝 Don't forget to set environment variables in Render dashboard"

elif [ "$DEPLOY_TARGET" = "render" ]; then
    echo "🚀 Deploying to Render..."
    echo "📝 Push to main branch to trigger Render auto-deploy via render.yaml"
    echo "📝 Or use Render CLI: render deploy --service omnimigrate-backend"

elif [ "$DEPLOY_TARGET" = "vps" ]; then
    echo "🚀 Deploying to VPS via Docker Compose..."

    if [ ! -f backend/.env.prod ]; then
        echo "❌ backend/.env.prod not found. Copy from backend/.env.prod.example"
        exit 1
    fi

    if [ ! -f frontend/.env.production ]; then
        echo "❌ frontend/.env.production not found. Create from frontend/.env.example"
        exit 1
    fi

    echo "🐳 Building and starting containers..."
    docker compose -f docker-compose.prod.yml up -d --build

    echo "⏳ Waiting for services to be healthy..."
    sleep 10

    echo "🔍 Checking health..."
    curl -f http://localhost/healthz || echo "Frontend health check failed"
    curl -f http://localhost/api/healthz || echo "Backend health check failed"

    echo "✅ VPS deployment complete!"
    echo "🌐 Access at http://yourdomain.com"

else
    echo "❌ Unknown target: $DEPLOY_TARGET"
    echo "Usage: ./deploy.sh [vercel|render|vps]"
    exit 1
fi

echo "🎉 Deployment complete!"