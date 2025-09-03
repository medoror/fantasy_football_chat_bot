# Fantasy Football Bot - Justfile

# Configuration
image_name := "game-bot"
tag := "latest"
namespace := "game-bot"
deployment_name := "game-bot"

# Show available commands
default:
    @just --list

# Build Docker image
build:
    @echo "🔨 Building Docker image..."
    docker build -t {{image_name}}:{{tag}} .

# Build and deploy to k3d
deploy:
    ./deploy-to-k3d.sh

# View bot logs
logs:
    kubectl logs -n {{namespace}} -l app={{deployment_name}} -f

# Check deployment status
status:
    @echo "📊 Deployment status:"
    kubectl get pods -n {{namespace}} -l app={{deployment_name}}
    @echo ""
    kubectl describe deployment {{deployment_name}} -n {{namespace}}

# Restart the deployment
restart:
    @echo "🔄 Restarting deployment..."
    kubectl rollout restart deployment/{{deployment_name}} -n {{namespace}}
    kubectl rollout status deployment/{{deployment_name}} -n {{namespace}}

# Delete the deployment
clean:
    @echo "🧹 Cleaning up deployment..."
    kubectl delete -f deployments/deployment.yaml || true

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
    k3d image import {{image_name}}:{{tag}}
    @echo "🔄 Restarting deployment..."
    kubectl rollout restart deployment/{{deployment_name}} -n {{namespace}}
    kubectl rollout status deployment/{{deployment_name}} -n {{namespace}}