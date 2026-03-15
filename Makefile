.PHONY: build build-execution run clean lint fmt vet tidy proto-gen contract-check

GATEWAY_BIN     := bin/gateway
EXECUTION_BIN   := bin/execution
GATEWAY_CMD     := ./src/gateway/cmd/gateway
EXECUTION_CMD   := ./src/execution/cmd/execution
PROTO_DIR       := proto

# Build flags for production: static binary, stripped symbols
LDFLAGS := -s -w
BUILD_FLAGS := -trimpath -ldflags "$(LDFLAGS)"

build:
	CGO_ENABLED=0 go build $(BUILD_FLAGS) -o $(GATEWAY_BIN) $(GATEWAY_CMD)

build-execution:
	CGO_ENABLED=0 go build $(BUILD_FLAGS) -o $(EXECUTION_BIN) $(EXECUTION_CMD)

build-all: build build-execution

run: build
	./$(GATEWAY_BIN)

run-execution: build-execution
	./$(EXECUTION_BIN)

clean:
	rm -rf bin/

tidy:
	go mod tidy

fmt:
	gofmt -s -w ./src/gateway/ ./src/execution/

vet:
	go vet ./src/gateway/... ./src/execution/...

contract-check:
	@echo "Validating processor contract (engine.proto <-> Python)..."
	python scripts/validate_processor_contract.py
	@echo "Contract check complete"

lint: vet fmt contract-check
	@echo "Lint passed"

proto-gen:
	@echo "Generating protobuf Go code..."
	protoc \
		--proto_path=$(PROTO_DIR) \
		--go_out=. --go_opt=paths=source_relative \
		--go-grpc_out=. --go-grpc_opt=paths=source_relative \
		$(PROTO_DIR)/engine/v1/engine.proto \
		$(PROTO_DIR)/gateway/v1/gateway.proto \
		$(PROTO_DIR)/execution/v1/execution.proto
	@echo "Proto generation complete"
