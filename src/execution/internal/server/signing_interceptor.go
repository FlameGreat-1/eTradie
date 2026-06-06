package server

import (
	"context"
	"strings"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/metadata"
	"google.golang.org/grpc/status"

	executionv1 "github.com/flamegreat-1/etradie/proto/execution/v1"
	"github.com/flamegreat-1/etradie/src/auth"
	"github.com/flamegreat-1/etradie/src/execution/internal/observability"
	"github.com/flamegreat-1/etradie/src/execution/internal/signing"
)

// ExecuteTradeFullMethod is the gRPC full-method name guarded by the
// signature interceptor. Kept as a const so the interceptor and any
// test reference the exact same string.
const ExecuteTradeFullMethod = "/execution.v1.ExecutionService/ExecuteTrade"

// boolLabel renders a bool as the metric label value.
func boolLabel(b bool) string {
	if b {
		return "true"
	}
	return "false"
}

// SigningVerifyInterceptor returns a gRPC unary server interceptor that
// verifies the HMAC signature + freshness + nonce on the ExecuteTrade
// RPC (CHECKLIST Tier 8: signed internal execution requests + replay
// protection).
//
// MUST be chained AFTER auth.UnaryAuthInterceptor so the authenticated
// claims are already in context; the canonical string binds the request
// to the JWT-resolved user_id, not to any wire-supplied value.
//
// enforce=false runs the gate in warn-only mode: every outcome is
// metered and an invalid request is logged at WARN but still passed
// through. This supports a phased rollout (deploy verifier + gateway
// signer, watch the metric show 100% ok, THEN flip enforce on).
//
// A nil verifier disables the gate entirely (defensive; the wiring in
// main.go only constructs a verifier when a key is available).
func SigningVerifyInterceptor(v *signing.Verifier, enforce bool) grpc.UnaryServerInterceptor {
	log := observability.Logger("signing_interceptor")
	enforcedLabel := boolLabel(enforce)

	return func(
		ctx context.Context,
		req interface{},
		info *grpc.UnaryServerInfo,
		handler grpc.UnaryHandler,
	) (interface{}, error) {
		// Guard only the money path; everything else is untouched.
		if v == nil || info.FullMethod != ExecuteTradeFullMethod {
			return handler(ctx, req)
		}

		// The auth interceptor (chained before this one) guarantees
		// claims are present for a guarded method; defend anyway.
		claims := auth.ClaimsFromContext(ctx)
		if claims == nil || claims.UserID == "" {
			return nil, status.Errorf(codes.Unauthenticated, "missing claims in context")
		}

		md, _ := metadata.FromIncomingContext(ctx)
		sig := firstMD(md, signing.MetaSignature)
		ts := firstMD(md, signing.MetaTimestamp)
		nonce := firstMD(md, signing.MetaNonce)

		if sig == "" || ts == "" || nonce == "" {
			observability.RequestSignatureTotal.WithLabelValues("missing", enforcedLabel).Inc()
			if enforce {
				return nil, status.Errorf(codes.PermissionDenied,
					"missing request signature metadata")
			}
			log.Warn().
				Str("user_id", claims.UserID).
				Msg("execute_trade_unsigned_warn_only_passthrough")
			return handler(ctx, req)
		}

		parsedTS, perr := time.Parse(time.RFC3339Nano, ts)
		if perr != nil {
			observability.RequestSignatureTotal.WithLabelValues("bad_signature", enforcedLabel).Inc()
			if enforce {
				return nil, status.Errorf(codes.PermissionDenied,
					"malformed request signature timestamp")
			}
			log.Warn().Err(perr).Str("user_id", claims.UserID).
				Msg("execute_trade_bad_timestamp_warn_only_passthrough")
			return handler(ctx, req)
		}

		// Build the canonical fields from the SAME inputs the gateway
		// signed: identity fields come from the verified claims +
		// metadata, request fields from the typed request.
		fields := signing.Fields{
			Timestamp:  parsedTS,
			Nonce:      nonce,
			UserID:     claims.UserID,
			Symbol:     executeTradeSymbol(req),
			Direction:  executeTradeDirection(req),
			AnalysisID: executeTradeAnalysisID(req),
		}

		outcome := v.Check(fields, sig, time.Now())
		observability.RequestSignatureTotal.WithLabelValues(outcome.String(), enforcedLabel).Inc()

		if outcome == signing.OutcomeOK {
			return handler(ctx, req)
		}

		if !enforce {
			log.Warn().
				Str("user_id", claims.UserID).
				Str("outcome", outcome.String()).
				Msg("execute_trade_signature_invalid_warn_only_passthrough")
			return handler(ctx, req)
		}

		log.Warn().
			Str("user_id", claims.UserID).
			Str("outcome", outcome.String()).
			Msg("execute_trade_rejected_invalid_signature")

		switch outcome {
		case signing.OutcomeStale, signing.OutcomeReplay:
			return nil, status.Errorf(codes.PermissionDenied,
				"request signature rejected: %s", outcome.String())
		default: // OutcomeBadSignature
			return nil, status.Errorf(codes.Unauthenticated,
				"request signature rejected: %s", outcome.String())
		}
	}
}

// executeTradeSymbol / executeTradeDirection / executeTradeAnalysisID
// extract the request fields bound into the canonical signing string.
// They type-assert to the concrete ExecuteTrade request; a non-match
// (impossible on the guarded method, but defended) yields "" so the
// canonical string is still deterministic and the signature simply
// fails to verify rather than panicking. Direction is upper-cased to
// match the gateway signer, which signs the normalised direction.
func executeTradeSymbol(req interface{}) string {
	if r, ok := req.(*executionv1.ExecuteTradeRequest); ok {
		return r.GetSymbol()
	}
	return ""
}

func executeTradeDirection(req interface{}) string {
	if r, ok := req.(*executionv1.ExecuteTradeRequest); ok {
		return strings.ToUpper(r.GetDirection())
	}
	return ""
}

func executeTradeAnalysisID(req interface{}) string {
	if r, ok := req.(*executionv1.ExecuteTradeRequest); ok {
		return r.GetAnalysisId()
	}
	return ""
}

// firstMD returns the first value for key in md, or "".
func firstMD(md metadata.MD, key string) string {
	if md == nil {
		return ""
	}
	vals := md.Get(key)
	if len(vals) == 0 {
		return ""
	}
	return vals[0]
}
