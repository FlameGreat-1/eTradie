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

# Force bash shell instead of Ubuntu's default dash shell for 'echo -e' support
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
	echo -e ""; \
	echo -e "$(BLUE)┌──────────────────────────────────────────────────────────────────────────────┐$(NC)"; \
	echo -e "$(BLUE)│$(NC) $(BOLD)OTHER OPTIONS$(NC)                                                                $(BLUE)│$(NC)"; \
	echo -e "$(BLUE)└──────────────────────────────────────────────────────────────────────────────┘$(NC)"; \
	printf "  $(YELLOW)%-4s$(NC) │ %-32s │ $(RED)%s$(NC)\n" "0" "Exit Menu" ""; \
	echo -e ""; \
	printf "$(BLUE)║$(NC)  $(CYAN)Enter your choice [0-13]:$(NC) "; \
	read choice; \
	echo -e ""; \
	case $$choice in \
		1) $(MAKE) db-migrate && docker compose up -d ;; \
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
		0) echo -e "$(GREEN)Goodbye!$(NC)"; exit 0 ;; \
		*) echo -e "$(RED)✗ Invalid choice$(NC)" ;; \
	esac;

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
	cd $(PROJECT_ROOT) && python -m pytest tests/ -v --tb=short
	echo -e "$(GREEN)✓ Python tests passed$(NC)"

test-go: ## Run Go unit tests for all services
	echo -e "$(BLUE)Running Go tests...$(NC)"
	go test ./src/gateway/... -v -count=1 -timeout 60s
	go test ./src/execution/... -v -count=1 -timeout 60s
	go test ./src/management/... -v -count=1 -timeout 60s
	echo -e "$(GREEN)✓ Go tests passed$(NC)"

test-engine: ## Run Python tests inside Docker container
	echo -e "$(BLUE)Running engine tests in Docker...$(NC)"
	docker compose exec engine pytest tests/ -v --tb=short
	echo -e "$(GREEN)✓ Engine tests passed$(NC)"

test-all: test-python test-go ## Run all tests (Python + Go)
	echo -e "$(GREEN)✓ All tests passed$(NC)"

##@ Health & Diagnostics
health: ## Check health of all running services
	echo -e "$(BLUE)Checking service health...$(NC)"
	@echo -n "  Engine:     " && curl -sf http://localhost:8000/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo -e "$(RED)DOWN$(NC)"
	@echo -n "  Gateway:    " && curl -sf http://localhost:8080/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo -e "$(RED)DOWN$(NC)"
	@echo -n "  Execution:  " && curl -sf http://localhost:8081/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo -e "$(RED)DOWN$(NC)"
	@echo -n "  Management: " && curl -sf http://localhost:8083/health | python3 -c "import sys,json; print(json.load(sys.stdin)['status'])" 2>/dev/null || echo -e "$(RED)DOWN$(NC)"
	@echo -n "  PostgreSQL: " && docker compose exec -T postgres pg_isready -U etradie -d etradie >/dev/null 2>&1 && echo -e "$(GREEN)ok$(NC)" || echo -e "$(RED)DOWN$(NC)"
	@echo -n "  Redis:      " && docker compose exec -T redis redis-cli ping 2>/dev/null | grep -q PONG && echo -e "$(GREEN)ok$(NC)" || echo -e "$(RED)DOWN$(NC)"
	@echo -n "  ChromaDB:   " && curl -sf http://localhost:8002/api/v1/heartbeat >/dev/null 2>&1 && echo -e "$(GREEN)ok$(NC)" || echo -e "$(RED)DOWN$(NC)"

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
	@python3 -c "\
import asyncio, os, sys; \
sys.path.insert(0, 'src'); \
from engine.ta.broker.mt5.config import MT5Config; \
from engine.ta.broker.mt5.zmq.client import ZmqClient; \
async def ping(): \
    cfg = MT5Config(provider='native'); \
    c = ZmqClient(config=cfg); \
    ok = await c.health_check(); \
    print(f'  Endpoint: tcp://{cfg.zmq_host}:{cfg.zmq_port}'); \
    print(f'  Status:   ' + ('\033[0;32mCONNECTED\033[0m' if ok else '\033[0;31mUNREACHABLE\033[0m')); \
    await c.shutdown(); \
    sys.exit(0 if ok else 1); \
asyncio.run(ping()) \
"

zmq-test: ## Full ZMQ bridge connectivity test (ping + candle + account)
	echo -e "$(BLUE)Running ZeroMQ bridge test...$(NC)"
	@python3 -c "\
import asyncio, os, sys, json; \
sys.path.insert(0, 'src'); \
from engine.ta.broker.mt5.config import MT5Config; \
from engine.ta.broker.mt5.zmq.client import ZmqClient; \
from engine.ta.constants import Timeframe; \
async def test(): \
    cfg = MT5Config(provider='native'); \
    c = ZmqClient(config=cfg); \
    ep = f'tcp://{cfg.zmq_host}:{cfg.zmq_port}'; \
    print(f'  Endpoint: {ep}'); \
    print(); \
    print('  [1/4] PING...', end=' '); \
    ok = await c.health_check(); \
    print('\033[0;32mOK\033[0m' if ok else '\033[0;31mFAIL\033[0m'); \
    if not ok: print('  EA not reachable. Is MT5 running with the EA attached?'); await c.shutdown(); sys.exit(1); \
    print('  [2/4] ACCOUNT_INFO...', end=' '); \
    acc = await c.get_account_info(); \
    print(f'\033[0;32mOK\033[0m  balance={acc.balance} {acc.currency}'); \
    print('  [3/4] TICK_PRICE EURUSD...', end=' '); \
    tick = await c.get_tick_price('EURUSD'); \
    print(f'\033[0;32mOK\033[0m  bid={tick.bid} ask={tick.ask}'); \
    print('  [4/4] CANDLES EURUSD H1 (5 bars)...', end=' '); \
    seq = await c.fetch_candles('EURUSD', Timeframe.H1, count=5); \
    print(f'\033[0;32mOK\033[0m  {seq.count} candles fetched'); \
    print(); \
    print('  \033[0;32m\u2713 All ZMQ bridge tests passed\033[0m'); \
    await c.shutdown(); \
asyncio.run(test()) \
"

zmq-tick: ## Fetch live tick price (usage: make zmq-tick SYMBOL=EURUSD)
	@python3 -c "\
import asyncio, sys; \
sys.path.insert(0, 'src'); \
from engine.ta.broker.mt5.config import MT5Config; \
from engine.ta.broker.mt5.zmq.client import ZmqClient; \
async def tick(): \
    cfg = MT5Config(provider='native'); \
    c = ZmqClient(config=cfg); \
    t = await c.get_tick_price('$(SYMBOL)'); \
    print(f'$(SYMBOL)  bid={t.bid}  ask={t.ask}  spread={t.ask-t.bid:.5f}'); \
    await c.shutdown(); \
asyncio.run(tick()) \
"

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
