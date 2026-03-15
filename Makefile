.PHONY: build run clean lint fmt vet tidy proto-gen

GATEWAY_BIN := bin/gateway
GATEWAY_CMD := ./src/gateway/cmd/gateway
PROTO_DIR   := proto

# Build flags for production: static binary, stripped symbols
LDFLAGS := -s -w
BUILD_FLAGS := -trimpath -ldflags "$(LDFLAGS)"

build:
	CGO_ENABLED=0 go build $(BUILD_FLAGS) -o $(GATEWAY_BIN) $(GATEWAY_CMD)

run: build
	./$(GATEWAY_BIN)

clean:
	rm -rf bin/

tidy:
	go mod tidy

fmt:
	gofmt -s -w ./src/gateway/

vet:
	go vet ./src/gateway/...

lint: vet fmt
	@echo "Lint passed"

proto-gen:
	@echo "Generating protobuf Go code..."
	protoc \
		--proto_path=$(PROTO_DIR) \
		--go_out=. --go_opt=paths=source_relative \
		--go-grpc_out=. --go-grpc_opt=paths=source_relative \
		$(PROTO_DIR)/engine/v1/engine.proto \
		$(PROTO_DIR)/gateway/v1/gateway.proto \
		$(PROTO_DIR)/processor/v1/processor.proto
	@echo "Proto generation complete"

contract-check:
	@echo "Validating processor contract..."
	python scripts/validate_processor_contract.py
	@echo "Contract check complete"
