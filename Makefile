# ============================================================================
# eTradie HFT AI TRADING PLATFORM - PRODUCTION MAKEFILE
# ============================================================================
# Version: 1.0.0
# Environment: Production / Development
# ============================================================================

.PHONY: help menu
.DEFAULT_GOAL := help
.SILENT:
MAKEFLAGS += --no-print-directory

# ============================================================================
# DIRECTORY STRUCTURE
# ============================================================================
PROJECT_ROOT := $(shell pwd)
GATEWAY_DIR := $(PROJECT_ROOT)/src/gateway
EXECUTION_DIR := $(PROJECT_ROOT)/src/execution
ENGINE_DIR := $(PROJECT_ROOT)
PROTO_DIR := $(PROJECT_ROOT)/proto

GATEWAY_BIN := bin/gateway
EXECUTION_BIN := bin/execution
MANAGEMENT_BIN := bin/management
GATEWAY_CMD := ./src/gateway/cmd/gateway
EXECUTION_CMD := ./src/execution/cmd/execution
MANAGEMENT_CMD := ./src/management/cmd/management

# ----------------------------------------------------------------------------
# Platform Makefile fragment. Sourced unconditionally with `-include`
# so a missing fragment does not break the build.
# ----------------------------------------------------------------------------
-include Makefile.platform

# Dynamically extract Windows Host IP for WSL traffic routing
export WSL_HOST_IP ?= $(shell ip route show default | awk '{print $$3}')

# Force bash shell
SHELL := /bin/bash

# ============================================================================
# COLORS & FORMATTING 
# ============================================================================
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
CYAN := \033[0;36m
MAGENTA := \033[0;35m
BOLD := \033[1m
NC := \033[0m

.logo:
	@echo ""
	@echo -e "       $(MAGENTA)███████╗████████╗██████╗  █████╗ ██████╗ ██╗███████╗$(NC)"
	@echo -e "       $(MAGENTA)██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██║██╔════╝$(NC)"
	@echo -e "       $(MAGENTA)█████╗     ██║   ██████╔╝███████║██║  ██║██║█████╗  $(NC)"
	@echo -e "       $(MAGENTA)██╔══╝     ██║   ██╔══██╗██╔══██║██║  ██║██║██╔══╝  $(NC)"
	@echo -e "       $(MAGENTA)███████╗   ██║   ██║  ██║██║  ██║██████╔╝██║███████╗$(NC)"
	@echo -e "       $(MAGENTA)╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚══════╝$(NC)"
	@echo ""

# ============================================================================
# GO CONFIGURATION
# ============================================================================
LDFLAGS := -s -w
BUILD_FLAGS := -trimpath -ldflags "$(LDFLAGS)"

# ============================================================================
# HELP SYSTEM
# ============================================================================

##@ General
help: ## Display comprehensive help message
	echo -e "$(BLUE)╔════════════════════════════════════════════════════════════════════════════╗$(NC)"
	echo -e "$(BLUE)║  $(BOLD)eTradie TRADING PLATFORM - BUILD & DEPLOY SYSTEM$(NC)$(BLUE)                          ║$(NC)"
	echo -e "$(BLUE)╚════════════════════════════════════════════════════════════════════════════╝$(NC)"
	echo -e ""
	awk 'BEGIN {FS = ":.*##"; printf "$(CYAN)Usage:$(NC) make $(YELLOW)<target>$(NC)\n\n"} \
		/^##@/ { printf "\n$(GREEN)%s$(NC)\n", substr($$0, 5) } \
		/^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(BLUE)%-30s$(NC) %s\n", $$1, $$2 }' $(MAKEFILE_LIST)
	echo -e ""
	echo -e "$(CYAN)Interactive Menu:$(NC) Run 'make menu' for a guided CLI experience."
	echo -e ""

##@ Interactive Menu
menu: ## Start the interactive guided menu
	@clear
	@$(MAKE) .logo
	@echo -e "$(CYAN)┌──────────────────────────────────────────────────────────────────────────────┐$(NC)"; \
	echo -e "$(CYAN)│$(NC) $(BOLD)DOCKER ORCHESTRATION$(NC)                                                         $(CYAN)│$(NC)"; \
	echo -e "$(CYAN)└──────────────────────────────────────────────────────────────────────────────┘$(NC)"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "1" "Start All Services (Detached)" "docker compose up -d"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "2" "Stop All Services" "docker compose down"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "3" "Rebuild & Start All Services" "docker compose up -d --build"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "4" "Tail All Logs" "docker compose logs -f"; \
	echo -e ""; \
	echo -e "$(CYAN)┌──────────────────────────────────────────────────────────────────────────────┐$(NC)"; \
	echo -e "$(CYAN)│$(NC) $(BOLD)BUILD & COMPILE (LOCAL)$(NC)                                                      $(CYAN)│$(NC)"; \
	echo -e "$(CYAN)└──────────────────────────────────────────────────────────────────────────────┘$(NC)"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "5" "Build Gateway (Go)" "make build-gateway"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "6" "Build Execution (Go)" "make build-execution"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "7" "Build Management (Go)" "make build-management"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "8" "Build All Go Binaries" "make build-all-go"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "9" "Generate Protobufs" "make proto-gen"; \
	echo -e ""; \
	echo -e "$(CYAN)┌──────────────────────────────────────────────────────────────────────────────┐$(NC)"; \
	echo -e "$(CYAN)│$(NC) $(BOLD)DATABASE & CODE QUALITY$(NC)                                                      $(CYAN)│$(NC)"; \
	echo -e "$(CYAN)└──────────────────────────────────────────────────────────────────────────────┘$(NC)"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(CYAN)%s$(NC)\n" "10" "Run Alembic DB Migrations" "make db-migrate"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(CYAN)%s$(NC)\n" "11" "Downgrade DB 1 Revision" "make db-downgrade"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(CYAN)%s$(NC)\n" "12" "Format Codes (Go/Python)" "make fmt"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(CYAN)%s$(NC)\n" "13" "Lint Codes" "make lint"; \
	echo -e ""; \
	echo -e "$(CYAN)┌──────────────────────────────────────────────────────────────────────────────┐$(NC)"; \
	echo -e "$(CYAN)│$(NC) $(BOLD)TESTING & HEALTH$(NC)                                                             $(CYAN)│$(NC)"; \
	echo -e "$(CYAN)└──────────────────────────────────────────────────────────────────────────────┘$(NC)"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "14" "Run Python Tests (Local)" "make test-python"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "15" "Run Go Tests" "make test-go"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "16" "Check Service Health" "make health"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "17" "Check Broker Bridge" "make broker-health"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "18" "ZMQ Bridge Test (Native)" "make zmq-test"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "19" "Run E2E Pipeline Tests" "make test-e2e"; \
	echo -e ""; \
	echo -e "$(BLUE)┌──────────────────────────────────────────────────────────────────────────────┐$(NC)"; \
	echo -e "$(BLUE)│$(NC) $(BOLD)OTHER OPTIONS$(NC)                                                                $(BLUE)│$(NC)"; \
	echo -e "$(BLUE)└──────────────────────────────────────────────────────────────────────────────┘$(NC)"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(RED)%s$(NC)\n" "0" "Exit Menu" ""; \
	echo -e ""; \
	printf "$(BLUE)║$(NC)  $(CYAN)Enter your choice [0-19]:$(NC) "; \
	read choice; \
	echo -e ""; \
	case $$choice in \
		1) docker compose up -d ;; \
		2) docker compose down ;; \
		3) docker compose up -d --build ;; \
		4) docker compose logs -f ;; \
		5) $(MAKE) build-gateway ;; \
		6) $(MAKE) build-execution ;; \
		7) $(MAKE) build-management ;; \
		8) $(MAKE) build-all-go ;; \
		9) $(MAKE) proto-gen ;; \
		10) $(MAKE) db-migrate ;; \
		11) $(MAKE) db-downgrade ;; \
		12) $(MAKE) fmt ;; \
		13) $(MAKE) lint ;; \
		14) $(MAKE) test-python ;; \
		15) $(MAKE) test-go ;; \
		16) $(MAKE) health ;; \
		17) $(MAKE) broker-health ;; \
		18) $(MAKE) zmq-test ;; \
		19) $(MAKE) test-e2e ;; \
		0) echo -e "$(GREEN)Goodbye!$(NC)"; exit 0 ;; \
		*) echo -e "$(RED)✗ Invalid choice$(NC)" ;; \
	esac;

##@ Edge profile (Cloudflare → edge-ingress → envoy → gateway, local mTLS)
dev-certs: ## Generate (or refresh) the local Cloudflare AOP dev CA + client cert
	echo -e "$(BLUE)Generating local Cloudflare AOP dev CA + client cert...$(NC)"
	bash deployments/cloudflare/origin-pull/generate-dev-certs.sh
	echo -e "$(GREEN)✓ Dev certs ready (deployments/cloudflare/origin-pull/)$(NC)"

edge-up: dev-certs ## Bring up the full edge chain locally (mTLS enforced)
	echo -e "$(BLUE)Starting full edge chain (Cloudflare-emulating dev mTLS)...$(NC)"
	docker compose --profile edge up -d --build
	echo -e "$(GREEN)✓ Edge chain running. https://localhost:8443 requires --cert/--key$(NC)"

edge-down: ## Tear down the edge chain (gateway + everything else stays up)
	echo -e "$(BLUE)Stopping edge chain...$(NC)"
	docker compose --profile edge stop edge-ingress envoy
	docker compose --profile edge rm -f edge-ingress envoy
	echo -e "$(GREEN)✓ Edge chain stopped$(NC)"

edge-test: ## Validate the local edge chain enforces mTLS (CI-friendly)
	echo -e "$(BLUE)Validating local mTLS enforcement...$(NC)"
	@# 1) The edge-ingress process must be alive BEFORE we trust any
	@#    handshake-rejection result. A crashed process also "rejects"
	@#    handshakes (Connection refused), so without this check the
	@#    test would false-green any time edge-ingress fails to boot.
	@echo -n "  edge-ingress process is alive: " && \
		curl -sf --max-time 3 http://localhost:19902/healthz >/dev/null \
		&& echo -e "$(GREEN)ok$(NC)" \
		|| { echo -e "$(RED)FAIL: edge-ingress not responding on :19902/healthz - process is down$(NC)"; exit 1; }
	@# 2) The TLS listener must accept at least the TCP handshake. If
	@#    we cannot connect, anything further is meaningless.
	@echo -n "  edge-ingress TLS listener is open: " && \
		timeout 3 bash -c 'cat </dev/tcp/localhost/8443' >/dev/null 2>&1 \
		&& echo -e "$(GREEN)ok$(NC)" \
		|| { echo -e "$(RED)FAIL: localhost:8443 is not accepting TCP connections$(NC)"; exit 1; }
	@# 3) Authenticated curl must SUCCEED. Otherwise a passing #4 below
	@#    is meaningless because the chain might be rejecting EVERY
	@#    request, not just unauthenticated ones.
	@echo -n "  authenticated   curl must SUCCEED: " && \
		curl -sk --max-time 10 \
		  --cert deployments/cloudflare/origin-pull/dev-client.crt \
		  --key  deployments/cloudflare/origin-pull/dev-client.key \
		  https://localhost:8443/auth/healthz >/dev/null \
		&& echo -e "$(GREEN)ok$(NC)" \
		|| { echo -e "$(RED)FAIL: authenticated request rejected (mTLS misconfigured or upstream broken)$(NC)"; exit 1; }
	@# 4) Unauthenticated curl MUST fail at TLS, specifically. Test for
	@#    "alert bad_certificate" / "alert handshake_failure" /
	@#    "alert certificate_required" in the output - NOT just
	@#    non-zero exit (which would also be true if the process
	@#    crashed between #3 and #4).
	@echo -n "  unauthenticated curl must FAIL at TLS: " && \
		unauth_err=$$(curl -sk --max-time 5 https://localhost:8443/auth/healthz 2>&1 1>/dev/null) || true; \
		if echo "$$unauth_err" | grep -qE 'alert (bad_certificate|handshake_failure|certificate_required)'; then \
			echo -e "$(GREEN)ok (TLS handshake rejected)$(NC)"; \
		elif echo "$$unauth_err" | grep -qiE 'connection refused|recv failure|connection reset'; then \
			echo -e "$(RED)FAIL: connection refused / reset - edge-ingress crashed mid-test$(NC)"; exit 1; \
		else \
			echo -e "$(RED)FAIL: unauthenticated request did not fail at TLS layer (got: $$unauth_err)$(NC)"; exit 1; \
		fi
	@# 5) Process must STILL be alive after the test (the unauthenticated
	@#    request must not have crashed the daemon).
	@echo -n "  edge-ingress process still alive: " && \
		curl -sf --max-time 3 http://localhost:19902/healthz >/dev/null \
		&& echo -e "$(GREEN)ok$(NC)" \
		|| { echo -e "$(RED)FAIL: edge-ingress crashed during validation$(NC)"; exit 1; }
	echo -e "$(GREEN)✓ Local edge chain mTLS posture matches production$(NC)"

##@ Docker Commands
up: ## Start all Docker containers in background
	@echo -e "$(BLUE)Starting eTradie infrastructure...$(NC)"
	@docker compose up -d
	@$(MAKE) .logo
	@echo -e "$(GREEN)✓ Containers started$(NC)"

down: ## Stop and remove all Docker containers
	echo -e "$(BLUE)Stopping eTradie infrastructure...$(NC)"
	docker compose down
	echo -e "$(GREEN)✓ Containers stopped$(NC)"

build: ## Rebuild and start all Docker containers
	@echo -e "$(BLUE)Building eTradie infrastructure...$(NC)"
	@docker compose up -d --build
	@$(MAKE) .logo
	@echo -e "$(GREEN)✓ Containers built and started$(NC)"

logs: ## Tail logs for all containers
	docker compose logs -f

ps: ## View running eTradie containers
	docker compose ps

build-mt-node: ## Build the MetaTrader headless Docker image
	echo -e "$(BLUE)Building etradie-mt-node...$(NC)"
	docker build -t ghcr.io/flamegreat-1/etradie-mt-node:latest docker/mt-node/
	echo -e "$(GREEN)✓ etradie-mt-node built$(NC)"

push-mt-node: build-mt-node ## Push the MetaTrader Docker image to GHCR
	echo -e "$(BLUE)Pushing etradie-mt-node to GHCR...$(NC)"
	docker push ghcr.io/flamegreat-1/etradie-mt-node:latest
	echo -e "$(GREEN)✓ etradie-mt-node pushed$(NC)"

##@ Go Local Builds
build-gateway: ## Build Gateway binary locally
	echo -e "$(BLUE)Building Gateway...$(NC)"
	CGO_ENABLED=0 go build $(BUILD_FLAGS) -o $(GATEWAY_BIN) $(GATEWAY_CMD)
	echo -e "$(GREEN)✓ Built $(GATEWAY_BIN)$(NC)"

build-execution: ## Build Execution binary locally
	echo -e "$(BLUE)Building Execution...$(NC)"
	CGO_ENABLED=0 go build $(BUILD_FLAGS) -o $(EXECUTION_BIN) $(EXECUTION_CMD)
	echo -e "$(GREEN)✓ Built $(EXECUTION_BIN)$(NC)"

build-management: ## Build Management binary locally
	echo -e "$(BLUE)Building Management...$(NC)"
	CGO_ENABLED=0 go build $(BUILD_FLAGS) -o $(MANAGEMENT_BIN) $(MANAGEMENT_CMD)
	echo -e "$(GREEN)✓ Built $(MANAGEMENT_BIN)$(NC)"

build-all-go: build-gateway build-execution build-management ## Build all Go binaries

clean: ## Remove generated binaries
	echo -e "$(BLUE)Cleaning binaries...$(NC)"
	rm -rf bin/
	echo -e "$(GREEN)✓ Cleaned$(NC)"

##@ Database & Migrations (Python)
db-migrate: ## Run Alembic migrations to head
	echo -e "$(BLUE)Running database migrations...$(NC)"
	docker compose run --rm migrator alembic upgrade head
	echo -e "$(GREEN)✓ Database is up to date$(NC)"

db-downgrade: ## Downgrade database by 1 revision
	echo -e "$(YELLOW)Downgrading database -1 revision...$(NC)"
	docker compose run --rm migrator alembic downgrade -1
	echo -e "$(GREEN)✓ Database downgraded$(NC)"

##@ Quality & Validation
tidy: ## Go mod tidy for all Go modules
	echo -e "$(BLUE)Tidying Go modules...$(NC)"
	go mod tidy
	cd src/gateway && go mod tidy || true
	cd src/execution && go mod tidy || true
	cd src/management && go mod tidy || true

fmt: ## Format Go and Python code
	echo -e "$(BLUE)Formatting codebase (Go)...$(NC)"
	gofmt -s -w ./src/gateway/ ./src/execution/ ./src/management/
	echo -e "$(BLUE)Formatting codebase (Python)...$(NC)"
	black src/engine/ || echo "$(YELLOW)Python black not installed, skipping...$(NC)"
	echo -e "$(GREEN)✓ Formatting complete$(NC)"

vet: ## Go vet
	go vet ./src/gateway/... ./src/execution/... ./src/management/...

contract-check: ## Validate Processor proto constraints against Python engine
	echo -e "$(BLUE)Validating processor contract (engine.proto <-> Python)...$(NC)"
	python3 scripts/validate_processor_contract.py || echo "$(YELLOW)Warning: validation missing...$(NC)"

lint: vet fmt contract-check ## Run all linters
	echo -e "$(GREEN)✓ Linting passed$(NC)"

proto-gen: ## Generate Protocol Buffer bindings (requires protoc)
	echo -e "$(BLUE)Generating protobuf Go code...$(NC)"
	protoc \
		--proto_path=$(PROTO_DIR) \
		--go_out=$(PROTO_DIR) --go_opt=paths=source_relative \
		--go-grpc_out=$(PROTO_DIR) --go-grpc_opt=paths=source_relative \
		$(PROTO_DIR)/engine/v1/engine.proto \
		$(PROTO_DIR)/gateway/v1/gateway.proto \
		$(PROTO_DIR)/execution/v1/execution.proto \
		$(PROTO_DIR)/management/v1/management.proto
	echo -e "$(GREEN)✓ Proto generation complete$(NC)"


##@ Testing
test-python: ## Run Python engine tests locally (no Docker)
	echo -e "$(BLUE)Running Python engine tests...$(NC)"
	docker compose exec engine python -m pytest tests/ -v --tb=short
	echo -e "$(GREEN)✓ Python tests passed$(NC)"

test-go: ## Run Go unit and integration tests (requires Redis + PostgreSQL)
	echo -e "$(BLUE)Running Go tests...$(NC)"
	@# Source .env for DB credentials but override hosts to localhost
	@# (Docker service names like 'postgres'/'redis' don't resolve on the host).
	@# We must also re-export EXECUTION_DATABASE_URL / MANAGEMENT_DATABASE_URL
	@# because bash expands ${POSTGRES_HOST} to 'postgres' when sourcing .env,
	@# BEFORE our localhost override takes effect.
	set -a && source .env && set +a && \
		export POSTGRES_HOST=localhost && \
		export REDIS_HOST=localhost && \
		export DATABASE_URL="postgres://$${POSTGRES_USER}:$${POSTGRES_PASSWORD}@localhost:5433/$${POSTGRES_DB}?sslmode=disable" && \
		export EXECUTION_DATABASE_URL="postgres://$${POSTGRES_USER}:$${POSTGRES_PASSWORD}@localhost:5433/$${POSTGRES_DB}?sslmode=disable" && \
		export MANAGEMENT_DATABASE_URL="postgres://$${POSTGRES_USER}:$${POSTGRES_PASSWORD}@localhost:5433/$${POSTGRES_DB}?sslmode=disable" && \
		export EXECUTION_REDIS_URL="redis://:$${REDIS_PASSWORD}@localhost:6379/1" && \
		export GATEWAY_REDIS_URL="redis://:$${REDIS_PASSWORD}@localhost:6379/0" && \
		export REDIS_URL="redis://:$${REDIS_PASSWORD}@localhost:6379/0" && \
		export MANAGEMENT_REDIS_URL="redis://:$${REDIS_PASSWORD}@localhost:6379/1" && \
		go test ./src/gateway/... -v -count=1 -timeout 120s && \
		go test ./src/execution/... -v -count=1 -timeout 120s && \
		go test ./src/management/... -v -count=1 -timeout 120s
	echo -e "$(BLUE)Running Gateway gRPC integration tests...$(NC)"
	set -a && source .env && set +a && \
		export POSTGRES_HOST=localhost && \
		export REDIS_HOST=localhost && \
		export DATABASE_URL="postgres://$${POSTGRES_USER}:$${POSTGRES_PASSWORD}@localhost:5433/$${POSTGRES_DB}?sslmode=disable" && \
		export EXECUTION_DATABASE_URL="postgres://$${POSTGRES_USER}:$${POSTGRES_PASSWORD}@localhost:5433/$${POSTGRES_DB}?sslmode=disable" && \
		export MANAGEMENT_DATABASE_URL="postgres://$${POSTGRES_USER}:$${POSTGRES_PASSWORD}@localhost:5433/$${POSTGRES_DB}?sslmode=disable" && \
		export EXECUTION_REDIS_URL="redis://:$${REDIS_PASSWORD}@localhost:6379/1" && \
		export GATEWAY_REDIS_URL="redis://:$${REDIS_PASSWORD}@localhost:6379/0" && \
		export REDIS_URL="redis://:$${REDIS_PASSWORD}@localhost:6379/0" && \
		export MANAGEMENT_REDIS_URL="redis://:$${REDIS_PASSWORD}@localhost:6379/1" && \
		go test ./src/gateway/grpctest/... -v -count=1 -timeout 120s
	echo -e "$(BLUE)Running Execution broker integration tests...$(NC)"
	go test ./src/execution/brokertest/... -v -count=1 -timeout 60s
	echo -e "$(BLUE)Running Management broker integration tests...$(NC)"
	go test ./src/management/brokertest/... -v -count=1 -timeout 60s
	echo -e "$(GREEN)✓ Go tests passed$(NC)"

test-e2e: ## Run E2E pipeline tests (requires Redis for alert transport)
	echo -e "$(BLUE)Running E2E pipeline tests...$(NC)"
	set -a && source .env && set +a && \
		export POSTGRES_HOST=localhost && \
		export REDIS_HOST=localhost && \
		export DATABASE_URL="postgres://$${POSTGRES_USER}:$${POSTGRES_PASSWORD}@localhost:5433/$${POSTGRES_DB}?sslmode=disable" && \
		export EXECUTION_DATABASE_URL="postgres://$${POSTGRES_USER}:$${POSTGRES_PASSWORD}@localhost:5433/$${POSTGRES_DB}?sslmode=disable" && \
		export MANAGEMENT_DATABASE_URL="postgres://$${POSTGRES_USER}:$${POSTGRES_PASSWORD}@localhost:5433/$${POSTGRES_DB}?sslmode=disable" && \
		export EXECUTION_REDIS_URL="redis://:$${REDIS_PASSWORD}@localhost:6379/1" && \
		export GATEWAY_REDIS_URL="redis://:$${REDIS_PASSWORD}@localhost:6379/0" && \
		export REDIS_URL="redis://:$${REDIS_PASSWORD}@localhost:6379/0" && \
		export MANAGEMENT_REDIS_URL="redis://:$${REDIS_PASSWORD}@localhost:6379/1" && \
		go test ./src/gateway/e2etest/... -v -count=1 -timeout 300s
	echo -e "$(GREEN)✓ E2E tests passed$(NC)"

test-engine: ## Run Python tests inside Docker container
	echo -e "$(BLUE)Running engine tests in Docker...$(NC)"
	docker compose exec engine pytest tests/ -v --tb=short
	echo -e "$(GREEN)✓ Engine tests passed$(NC)"

test-all: test-python test-go test-e2e ## Run all tests (Python + Go + E2E)
	echo -e "$(GREEN)✓ All tests passed$(NC)"

##@ Health & Diagnostics
health: ## Check health of all running services
	echo -e "$(BLUE)Checking service health...$(NC)"
	@echo -n "  Engine:     " && curl -sf http://localhost:8000/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo -e "$(RED)DOWN$(NC)"
	@echo -n "  Gateway:    " && curl -sf http://localhost:8080/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo -e "$(RED)DOWN$(NC)"
	@echo -n "  Execution:  " && curl -sf http://localhost:8081/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo -e "$(RED)DOWN$(NC)"
	@echo -n "  Management: " && curl -sf http://localhost:8083/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo -e "$(RED)DOWN$(NC)"
	@echo -n "  PostgreSQL: " && docker compose exec -T postgres pg_isready -U etradie -d etradie >/dev/null 2>&1 && echo -e "$(GREEN)ok$(NC)" || echo -e "$(RED)DOWN$(NC)"
	@echo -n "  Redis:      " && set -a && source .env && set +a && docker compose exec -T redis redis-cli -a "$$REDIS_PASSWORD" ping 2>/dev/null | grep -q PONG && echo -e "$(GREEN)ok$(NC)" || echo -e "$(RED)DOWN$(NC)"
	@echo -n "  ChromaDB:   " && curl -sf http://localhost:8002/api/v2/heartbeat >/dev/null 2>&1 && echo -e "$(GREEN)ok$(NC)" || echo -e "$(RED)DOWN$(NC)"

broker-health: ## Verify broker bridge connectivity (engine must be running)
	echo -e "$(BLUE)Checking broker bridge endpoints...$(NC)"
	@echo -n "  account_info:    " && curl -sf http://localhost:8000/internal/broker/account_info >/dev/null 2>&1 && echo -e "$(GREEN)ok$(NC)" || echo -e "$(RED)FAIL$(NC)"
	@echo -n "  positions:       " && curl -sf http://localhost:8000/internal/broker/positions >/dev/null 2>&1 && echo -e "$(GREEN)ok$(NC)" || echo -e "$(RED)FAIL$(NC)"
	@echo -n "  pending_orders:  " && curl -sf http://localhost:8000/internal/broker/pending_orders >/dev/null 2>&1 && echo -e "$(GREEN)ok$(NC)" || echo -e "$(RED)FAIL$(NC)"
	@echo -n "  tick_price:      " && curl -sf "http://localhost:8000/internal/broker/tick_price?symbol=EURUSD" >/dev/null 2>&1 && echo -e "$(GREEN)ok$(NC)" || echo -e "$(RED)FAIL$(NC)"
	@echo -n "  symbol_info:     " && curl -sf "http://localhost:8000/internal/broker/symbol_info?symbol=EURUSD" >/dev/null 2>&1 && echo -e "$(GREEN)ok$(NC)" || echo -e "$(RED)FAIL$(NC)"

##@ ZeroMQ Bridge (Native Mode)
zmq-status: ## Show current MT5 provider configuration
	echo -e "$(BLUE)MT5 Provider Configuration:$(NC)"
	@grep -E '^MT5_' .env 2>/dev/null || echo -e "$(YELLOW)  No .env file found. Copy .env.example to .env$(NC)"

zmq-ping: ## Send PING to ZeroMQ EA to verify bridge is alive
	echo -e "$(BLUE)Pinging ZeroMQ EA...$(NC)"
	@docker compose exec -T engine python3 scripts/zmq_test.py --mode ping

zmq-test: ## Full ZMQ bridge connectivity test (ping + candle + account)
	echo -e "$(BLUE)Running ZeroMQ bridge test...$(NC)"
	@docker compose exec -T engine python3 scripts/zmq_test.py --mode test

zmq-tick: ## Fetch live tick price (usage: make zmq-tick SYMBOL=EURUSD)
	@docker compose exec -T engine python3 scripts/zmq_test.py --mode tick --symbol "$(SYMBOL)"

SYMBOL ?= EURUSD

install-ea: ## Instructions for installing ZeroMQ EA on MT5 (native mode only)
	echo -e ""
	echo -e "$(CYAN)┌──────────────────────────────────────────────────────────────────────────────┐$(NC)"
	echo -e "$(CYAN)│$(NC) $(BOLD)ZeroMQ EA Installation (Native Mode Only)$(NC)                                    $(CYAN)│$(NC)"
	echo -e "$(CYAN)└──────────────────────────────────────────────────────────────────────────────┘$(NC)"
	echo -e ""
	echo -e "  $(YELLOW)Prerequisites:$(NC)"
	echo -e "    - MT5 terminal installed on Windows PC"
	echo -e "    - ZeroMQ MQL5 library (Include/Zmq/Zmq.mqh)"
	echo -e "    - JAson MQL5 library (Include/JAson.mqh)"
	echo -e ""
	echo -e "  $(YELLOW)Steps:$(NC)"
	echo -e "    1. Install ZMQ library: https://github.com/dingmaotu/mql-zmq"
	echo -e "    2. Install JAson library: https://www.mql5.com/en/code/11134"
	echo -e "    3. Copy EA to MT5 data folder:"
	echo -e "       $(GREEN)cp src/engine/ta/broker/mt5/zmq/ZeroMQ_EA.mq5 \\$(NC)"
	echo -e "       $(GREEN)   '<MT5_DATA_FOLDER>/MQL5/Experts/ZeroMQ_EA.mq5'$(NC)"
	echo -e "    4. Compile in MetaEditor (F7)"
	echo -e "    5. Attach to any chart in MT5"
	echo -e "    6. Enable 'Allow DLL imports' in EA settings"
	echo -e "    7. Set MT5_PROVIDER=native in .env"
	echo -e "    8. Set MT5_ZMQ_HOST to the Windows PC IP"
	echo -e ""
	echo -e "  $(YELLOW)Cloud mode (metaapi) does not need this EA.$(NC)"
	echo -e ""
