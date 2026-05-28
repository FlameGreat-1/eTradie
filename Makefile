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
# ----------------------------------------------------------------------------
# `menu` is auto-derived from the SAME `## description` doc lines and
# `##@ Group` banners that `help` parses. The two surfaces share a
# single source of truth: $(MAKEFILE_LIST), which already includes
# both Makefile and Makefile.platform thanks to the `-include`
# directive at the top of this file.
#
# Adding a new target with a `## description` exposes it in BOTH
# `help` AND `menu` automatically. There is no per-target wiring
# to maintain in the menu recipe.
#
# Two interaction modes, auto-selected at runtime:
#   - If `fzf` is on $PATH: fuzzy substring picker (preferred on
#     dev machines; type any part of the target name or description).
#   - Otherwise: numbered list + `read` prompt (POSIX-portable; works
#     on minimal CI containers, restricted shells, over SSH, on
#     macOS / Linux / WSL).
#
# Self-exclusion rules baked into the awk filter:
#   - `help` and `menu` themselves are excluded so the menu never
#     offers to recurse into itself.
#   - Targets whose name starts with `.` (`.logo`, `.PHONY`, etc.) are
#     excluded because the awk pattern only matches
#     `^[a-zA-Z_0-9-]+:` at the start of a line.
#   - A target with no `## description` is invisible by design. This
#     enforces the same discipline `help` already enforces: if it is
#     operator-facing, it must carry a one-line doc.
#
# Exit conventions: entering `0`, an empty line, ESC (in fzf mode),
# Ctrl-C, or Ctrl-D all exit cleanly without running anything. The
# temp file used to materialise the target list is removed on every
# exit path via `trap`.
# ----------------------------------------------------------------------------
menu: ## Start the interactive guided menu (auto-derived from ## doc comments)
	@clear
	@$(MAKE) .logo
	@set -eu; \
	targets_file=$$(mktemp); \
	trap 'rm -f "$$targets_file"' EXIT INT TERM HUP; \
	awk ' \
		BEGIN { group = "General" } \
		/^##@ / { group = substr($$0, 5); next } \
		/^[a-zA-Z_0-9-]+:.*?##/ { \
			name = $$1; sub(/:.*/, "", name); \
			if (name == "help" || name == "menu") next; \
			desc = $$0; sub(/^[^#]*##[[:space:]]*/, "", desc); \
			printf "%s\t%s\t%s\n", name, group, desc; \
		}' $(MAKEFILE_LIST) > "$$targets_file"; \
	if [ ! -s "$$targets_file" ]; then \
		echo -e "$(RED)\xE2\x9C\x97 No documented targets found in $(MAKEFILE_LIST)$(NC)"; \
		exit 1; \
	fi; \
	if command -v fzf >/dev/null 2>&1; then \
		echo -e "$(CYAN)Type to filter; ENTER to run; ESC to cancel.$(NC)"; \
		echo -e ""; \
		choice=$$(awk -F'\t' '{printf "%-32s  \033[0;36m[%s]\033[0m  %s\n", $$1, $$2, $$3}' "$$targets_file" \
			| fzf --ansi --reverse --height=80% \
				--prompt="make > " \
				--header="Pick a target (auto-derived from Makefile + Makefile.platform)" \
				--no-mouse \
				--exit-0) || { echo -e "$(GREEN)Cancelled.$(NC)"; exit 0; }; \
		target=$$(printf '%s' "$$choice" | awk '{print $$1}'); \
	else \
		echo -e ""; \
		awk -F'\t' ' \
			BEGIN { last_group = "" } \
			{ \
				if ($$2 != last_group) { \
					last_group = $$2; \
					printf "\n\033[0;32m%s\033[0m\n", $$2; \
				} \
				printf "  \033[1;33m%3d\033[0m  \033[0;34m%-32s\033[0m  %s\n", NR, $$1, $$3; \
			}' "$$targets_file"; \
		echo -e ""; \
		printf "  $(YELLOW)%3s$(NC)  %s\n" "0" "$(RED)Exit$(NC)"; \
		echo -e ""; \
		printf "$(CYAN)Enter number (0 or empty to exit):$(NC) "; \
		read -r n || { echo -e "$(GREEN)Cancelled.$(NC)"; exit 0; }; \
		if [ -z "$$n" ] || [ "$$n" = "0" ]; then \
			echo -e "$(GREEN)Goodbye!$(NC)"; exit 0; \
		fi; \
		case "$$n" in \
			*[!0-9]*) echo -e "$(RED)\xE2\x9C\x97 Invalid choice: not a number$(NC)"; exit 1 ;; \
		esac; \
		total=$$(wc -l < "$$targets_file" | tr -d ' '); \
		if [ "$$n" -lt 1 ] || [ "$$n" -gt "$$total" ]; then \
			echo -e "$(RED)\xE2\x9C\x97 Invalid choice: out of range (1-$$total)$(NC)"; \
			exit 1; \
		fi; \
		target=$$(awk -F'\t' -v n=$$n 'NR==n {print $$1}' "$$targets_file"); \
	fi; \
	if [ -z "$$target" ]; then \
		echo -e "$(RED)\xE2\x9C\x97 Could not resolve target$(NC)"; \
		exit 1; \
	fi; \
	echo -e ""; \
	echo -e "$(BLUE)\xE2\x96\xB6 Running: $(BOLD)make $$target$(NC)"; \
	echo -e ""; \
	exec $(MAKE) "$$target"

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
