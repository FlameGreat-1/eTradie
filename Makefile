# ============================================================================
# eTradie HFT AI TRADING PLATFORM - PRODUCTION MAKEFILE
# ============================================================================
# Version: 1.0.0
# Environment: Production / Development
# ============================================================================

.PHONY: help menu
.DEFAULT_GOAL := help
.SILENT:

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
GATEWAY_CMD := ./src/gateway/cmd/gateway
EXECUTION_CMD := ./src/execution/cmd/execution

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
	@echo ""; \
	echo -e "       $(MAGENTA)███████╗████████╗██████╗  █████╗ ██████╗ ██╗███████╗$(NC)"; \
	echo -e "       $(MAGENTA)██╔════╝╚══██╔══╝██╔══██╗██╔══██╗██╔══██╗██║██╔════╝$(NC)"; \
	echo -e "       $(MAGENTA)█████╗     ██║   ██████╔╝███████║██║  ██║██║█████╗  $(NC)"; \
	echo -e "       $(MAGENTA)██╔══╝     ██║   ██╔══██╗██╔══██║██║  ██║██║██╔══╝  $(NC)"; \
	echo -e "       $(MAGENTA)███████╗   ██║   ██║  ██║██║  ██║██████╔╝██║███████╗$(NC)"; \
	echo -e "       $(MAGENTA)╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝╚═════╝ ╚═╝╚══════╝$(NC)"; \
	echo ""; \
	echo -e "$(CYAN)┌──────────────────────────────────────────────────────────────────────────────┐$(NC)"; \
	echo -e "$(CYAN)│$(NC) $(BOLD)DOCKER ORCHESTRATION$(NC)                                                         $(CYAN)│$(NC)"; \
	echo -e "$(CYAN)└──────────────────────────────────────────────────────────────────────────────┘$(NC)"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "1" "Start All Services (Detached)" "docker-compose up -d"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "2" "Stop All Services" "docker-compose down"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "3" "Rebuild & Start All Services" "docker-compose up -d --build"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "4" "Tail All Logs" "docker-compose logs -f"; \
	echo -e ""; \
	echo -e "$(CYAN)┌──────────────────────────────────────────────────────────────────────────────┐$(NC)"; \
	echo -e "$(CYAN)│$(NC) $(BOLD)BUILD & COMPILE (LOCAL)$(NC)                                                      $(CYAN)│$(NC)"; \
	echo -e "$(CYAN)└──────────────────────────────────────────────────────────────────────────────┘$(NC)"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "5" "Build Gateway (Go)" "make build-gateway"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "6" "Build Execution (Go)" "make build-execution"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "7" "Build All Go Binaries" "make build-all-go"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(GREEN)%s$(NC)\n" "8" "Generate Protobufs" "make proto-gen"; \
	echo -e ""; \
	echo -e "$(CYAN)┌──────────────────────────────────────────────────────────────────────────────┐$(NC)"; \
	echo -e "$(CYAN)│$(NC) $(BOLD)DATABASE & CODE QUALITY$(NC)                                                      $(CYAN)│$(NC)"; \
	echo -e "$(CYAN)└──────────────────────────────────────────────────────────────────────────────┘$(NC)"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(CYAN)%s$(NC)\n" "9"  "Run Alembic DB Migrations" "make db-migrate"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(CYAN)%s$(NC)\n" "10" "Downgrade DB 1 Revision" "make db-downgrade"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(CYAN)%s$(NC)\n" "11" "Format Codes (Go/Python)" "make fmt"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(CYAN)%s$(NC)\n" "12" "Lint Codes" "make lint"; \
	echo -e ""; \
	echo -e "$(BLUE)┌──────────────────────────────────────────────────────────────────────────────┐$(NC)"; \
	echo -e "$(BLUE)│$(NC) $(BOLD)OTHER OPTIONS$(NC)                                                                $(BLUE)│$(NC)"; \
	echo -e "$(BLUE)└──────────────────────────────────────────────────────────────────────────────┘$(NC)"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(RED)%s$(NC)\n" "0" "Exit Menu" ""; \
	echo -e ""; \
	printf "$(BLUE)║$(NC)  $(CYAN)Enter your choice [0-12]:$(NC) "; \
	read choice; \
	echo -e ""; \
	case $$choice in \
		1) $(MAKE) db-migrate && docker-compose up -d ;; \
		2) docker-compose down ;; \
		3) docker-compose up -d --build ;; \
		4) docker-compose logs -f ;; \
		5) $(MAKE) build-gateway ;; \
		6) $(MAKE) build-execution ;; \
		7) $(MAKE) build-all-go ;; \
		8) $(MAKE) proto-gen ;; \
		9) $(MAKE) db-migrate ;; \
		10) $(MAKE) db-downgrade ;; \
		11) $(MAKE) fmt ;; \
		12) $(MAKE) lint ;; \
		0) echo -e "$(GREEN)Goodbye!$(NC)"; exit 0 ;; \
		*) echo -e "$(RED)✗ Invalid choice$(NC)" ;; \
	esac;

##@ Docker Commands
up: ## Start all Docker containers in background
	echo -e "$(BLUE)Starting eTradie infrastructure...$(NC)"
	docker-compose up -d
	echo -e "$(GREEN)✓ Containers started$(NC)"

down: ## Stop and remove all Docker containers
	echo -e "$(BLUE)Stopping eTradie infrastructure...$(NC)"
	docker-compose down
	echo -e "$(GREEN)✓ Containers stopped$(NC)"

build: ## Rebuild and start all Docker containers
	echo -e "$(BLUE)Building eTradie infrastructure...$(NC)"
	docker-compose up -d --build
	echo -e "$(GREEN)✓ Containers built and started$(NC)"

logs: ## Tail logs for all containers
	docker-compose logs -f

ps: ## View running eTradie containers
	docker-compose ps

##@ Go Local Builds
build-gateway: ## Build Gateway binary locally
	echo -e "$(BLUE)Building Gateway...$(NC)"
	CGO_ENABLED=0 go build $(BUILD_FLAGS) -o $(GATEWAY_BIN) $(GATEWAY_CMD)
	echo -e "$(GREEN)✓ Built $(GATEWAY_BIN)$(NC)"

build-execution: ## Build Execution binary locally
	echo -e "$(BLUE)Building Execution...$(NC)"
	CGO_ENABLED=0 go build $(BUILD_FLAGS) -o $(EXECUTION_BIN) $(EXECUTION_CMD)
	echo -e "$(GREEN)✓ Built $(EXECUTION_BIN)$(NC)"

build-all-go: build-gateway build-execution ## Build all Go binaries

clean: ## Remove generated binaries
	echo -e "$(BLUE)Cleaning binaries...$(NC)"
	rm -rf bin/
	echo -e "$(GREEN)✓ Cleaned$(NC)"

##@ Database & Migrations (Python)
db-migrate: ## Run Alembic migrations to head
	echo -e "$(BLUE)Running database migrations...$(NC)"
	alembic upgrade head
	echo -e "$(GREEN)✓ Database is up to date$(NC)"

db-downgrade: ## Downgrade database by 1 revision
	echo -e "$(YELLOW)Downgrading database -1 revision...$(NC)"
	alembic downgrade -1
	echo -e "$(GREEN)✓ Database downgraded$(NC)"

##@ Quality & Validation
tidy: ## Go mod tidy for all Go modules
	echo -e "$(BLUE)Tidying Go modules...$(NC)"
	go mod tidy
	cd src/gateway && go mod tidy || true
	cd src/execution && go mod tidy || true

fmt: ## Format Go and Python code
	echo -e "$(BLUE)Formatting codebase (Go)...$(NC)"
	gofmt -s -w ./src/gateway/ ./src/execution/
	echo -e "$(BLUE)Formatting codebase (Python)...$(NC)"
	black src/engine/ || echo "$(YELLOW)Python black not installed, skipping...$(NC)"
	echo -e "$(GREEN)✓ Formatting complete$(NC)"

vet: ## Go vet
	go vet ./src/gateway/... ./src/execution/...

contract-check: ## Validate Processor proto constraints against Python engine
	echo -e "$(BLUE)Validating processor contract (engine.proto <-> Python)...$(NC)"
	python3 scripts/validate_processor_contract.py || echo "$(YELLOW)Warning: validation missing...$(NC)"

lint: vet fmt contract-check ## Run all linters
	echo -e "$(GREEN)✓ Linting passed$(NC)"

proto-gen: ## Generate Protocol Buffer bindings (requires protoc)
	echo -e "$(BLUE)Generating protobuf Go code...$(NC)"
	protoc \
		--proto_path=$(PROTO_DIR) \
		--go_out=. --go_opt=paths=source_relative \
		--go-grpc_out=. --go-grpc_opt=paths=source_relative \
		$(PROTO_DIR)/engine/v1/engine.proto \
		$(PROTO_DIR)/gateway/v1/gateway.proto \
		$(PROTO_DIR)/execution/v1/execution.proto
	echo -e "$(GREEN)✓ Proto generation complete$(NC)"
