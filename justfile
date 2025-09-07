# Fantasy Football Bot - Justfile

# Configuration
image_name := "game-bot"
tag := `date +%Y%m%d-%H%M%S`
namespace := "game-bot"
release_name := "game-bot"
chart_path := "./helm/game-bot"
cluster_name := "mycluster"

# Show available commands
default:
    @just --list

# Build Docker image
build:
    @echo "🔨 Building Docker image..."
    docker build -t {{image_name}}:{{tag}} .

# Build and deploy with Helm
deploy: build
    @echo "📦 Loading image into k3d..."
    k3d image import {{image_name}}:{{tag}} --cluster {{cluster_name}}
    @echo "🚀 Deploying with Helm..."
    @if [ -z "$DISCORD_WEBHOOK_URL" ]; then echo "❌ DISCORD_WEBHOOK_URL environment variable is required"; exit 1; fi
    helm upgrade --install {{release_name}} {{chart_path}} \
        --namespace {{namespace}} \
        --create-namespace \
        --set image.tag={{tag}} \
        --set secrets.discordWebhookUrl="$DISCORD_WEBHOOK_URL"
    @echo "⏳ Waiting for deployment..."
    kubectl rollout status deployment/{{release_name}} -n {{namespace}}

# View bot logs
logs:
    kubectl logs -n {{namespace}} -l app.kubernetes.io/name={{release_name}} -f

# Check deployment status
status:
    @echo "📊 Deployment status:"
    helm status {{release_name}} -n {{namespace}}
    @echo ""
    kubectl get pods -n {{namespace}} -l app.kubernetes.io/name={{release_name}}

# Restart the deployment
restart:
    @echo "🔄 Restarting deployment..."
    kubectl rollout restart deployment/{{release_name}} -n {{namespace}}
    kubectl rollout status deployment/{{release_name}} -n {{namespace}}

# Delete the deployment
clean:
    @echo "🧹 Cleaning up deployment..."
    helm uninstall {{release_name}} -n {{namespace}} || true

# Run tests
test:
    @echo "🧪 Running tests..."
    pip install -r requirements-test.txt
    pytest

# Run linter
lint:
    @echo "🔍 Running linter..."
    flake8

# Quick build and restart (for faster development)
quick: build
    @echo "📦 Loading image into k3d..."
    k3d image import {{image_name}}:{{tag}} --cluster {{cluster_name}}
    @echo "🔄 Upgrading Helm release..."
    @if [ -z "$DISCORD_WEBHOOK_URL" ]; then echo "❌ DISCORD_WEBHOOK_URL environment variable is required"; exit 1; fi
    helm upgrade {{release_name}} {{chart_path}} \
        --namespace {{namespace}} \
        --set image.tag={{tag}} \
        --set secrets.discordWebhookUrl="$DISCORD_WEBHOOK_URL"
    kubectl rollout status deployment/{{release_name}} -n {{namespace}}

# Validate Helm chart
validate:
    @echo "🔍 Validating Helm chart..."
    helm lint {{chart_path}}
    @echo "📋 Dry run deployment..."
    @if [ -z "$DISCORD_WEBHOOK_URL" ]; then echo "❌ DISCORD_WEBHOOK_URL environment variable is required"; exit 1; fi
    helm template {{release_name}} {{chart_path}} \
        --namespace {{namespace}} \
        --set image.tag={{tag}} \
        --set secrets.discordWebhookUrl="$DISCORD_WEBHOOK_URL" \
        --dry-run