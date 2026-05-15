// Package pulse provides a fire-and-forget publisher for real-time
// analysis status updates. It publishes JSON "pulse" frames to the
// user's private SSE channel (etradie:stream:user:{user_id}), which
// the existing Python SSE endpoint forwards to the browser.
//
// The Go-side pulse publisher mirrors the Python PulsePublisher in
// src/engine/shared/pulse/publisher.py. Both emit identical frame
// shapes so the frontend ThinkingTerminal renders them consistently
// regardless of which service triggered the analysis cycle.
//
// Safety: Every Emit call is fire-and-forget. A failed publish never
// blocks, panics, or delays the analysis pipeline.
package pulse

import (
	"context"
	"encoding/json"
	"fmt"

	goredis "github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"
)

const streamNamespace = "etradie:stream:user"

// frame is the JSON shape published to the SSE channel. It must
// exactly match the Python PulsePublisher's output and the frontend
// ServerFrame union type (type: 'pulse').
type frame struct {
	Type      string `json:"type"`
	Symbol    string `json:"symbol"`
	Phase     string `json:"phase"`
	Message   string `json:"message"`
	Source    string `json:"source"`
	Completed bool   `json:"completed"`
}

// Publisher emits granular analysis status updates to the user's
// private SSE channel via Redis pub/sub.
type Publisher struct {
	client  *goredis.Client
	channel string
	symbol  string
	log     zerolog.Logger
}

// NewPublisher creates a Publisher scoped to a specific user and symbol.
// If client is nil, all Emit calls are silent no-ops.
func NewPublisher(client *goredis.Client, userID, symbol string, log zerolog.Logger) *Publisher {
	return &Publisher{
		client:  client,
		channel: fmt.Sprintf("%s:%s", streamNamespace, userID),
		symbol:  symbol,
		log:     log,
	}
}

// Emit publishes a single pulse frame. Fire-and-forget: errors are
// logged at debug level but never returned or propagated.
//
// Args:
//
//	phase:     Hacker-verb category (SHARDING, DETECTING, CLAUDING, …).
//	message:   Human-readable sub-step description.
//	source:    Origin component (ta, macro, rag, processor).
//	completed: True when this phase has finished processing.
func (p *Publisher) Emit(ctx context.Context, phase, message, source string, completed bool) {
	if p == nil || p.client == nil {
		return
	}

	f := frame{
		Type:      "pulse",
		Symbol:    p.symbol,
		Phase:     phase,
		Message:   message,
		Source:    source,
		Completed: completed,
	}

	data, err := json.Marshal(f)
	if err != nil {
		p.log.Debug().Err(err).Str("phase", phase).Msg("pulse_marshal_failed")
		return
	}

	if err := p.client.Publish(ctx, p.channel, data).Err(); err != nil {
		p.log.Debug().Err(err).Str("phase", phase).Msg("pulse_publish_failed")
	}
}

// NoOp is a nil-safe Publisher that does nothing. Use as a
// zero-allocation alternative when pulse broadcasting is not needed.
var NoOp *Publisher = nil
