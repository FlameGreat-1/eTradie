package auth

import (
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
)

// MaxJSONBodyBytes is the default upper bound on the size of a JSON
// request body the API will read before rejecting the request. It is
// deliberately generous (256 KiB) relative to the small, flat request
// shapes every endpoint accepts (a handful of string/int fields, or a
// modest array of symbols) yet far below any value that could threaten
// gateway memory under a flood.
//
// TIER 4 "Length limits": the edge-ingress is an L4 TCP/TLS proxy
// (copy_bidirectional) and the Envoy L7 config sets no
// max_request_bytes, so this is the authoritative request-body size
// limit for the platform. An oversized body cannot be streamed into
// json.Decode beyond this bound because http.MaxBytesReader fails the
// read first.
const MaxJSONBodyBytes int64 = 256 * 1024

// DecodeJSONStrict decodes exactly one JSON value from the request body
// into dst with the strict posture required by TIER 4 input
// validation:
//
//   - the body is capped at maxBytes via http.MaxBytesReader, so an
//     oversized payload is rejected (413) instead of being buffered
//     into memory by the decoder ("Length limits");
//   - DisallowUnknownFields is set, so a body carrying any field not
//     present in dst is rejected ("Reject unknown fields");
//   - the body must contain exactly ONE JSON value — trailing tokens
//     or a second value (request smuggling / accidental concatenation)
//     are rejected.
//
// maxBytes <= 0 selects MaxJSONBodyBytes. The caller passes the
// http.ResponseWriter so MaxBytesReader can set the connection-close
// signal on overflow. Type enforcement is provided by encoding/json
// itself: a value of the wrong JSON type for a typed struct field is a
// decode error here, surfaced as 400 by DecodeJSONError.
//
// An empty body is an error (io.EOF from the decoder). Callers whose
// body is OPTIONAL must use DecodeJSONStrictAllowEmpty instead.
//
// On error the caller maps it with DecodeJSONError to obtain the
// correct HTTP status (413 for an over-limit body, 400 otherwise).
func DecodeJSONStrict(w http.ResponseWriter, r *http.Request, dst interface{}, maxBytes int64) error {
	return decodeJSON(w, r, dst, maxBytes, false)
}

// DecodeJSONStrictAllowEmpty behaves exactly like DecodeJSONStrict
// except that a COMPLETELY EMPTY body is accepted and leaves dst at its
// zero value (returning nil). This is the correct primitive for
// endpoints whose body is optional — e.g. the OAuth start endpoints,
// where an absent body simply means "no return_to". A non-empty body is
// still validated under the full strict posture (size cap, unknown
// fields, single value).
//
// "Empty" means the very first read yields io.EOF. A truncated or
// malformed non-empty body is still a 400, never silently treated as
// empty.
func DecodeJSONStrictAllowEmpty(w http.ResponseWriter, r *http.Request, dst interface{}, maxBytes int64) error {
	return decodeJSON(w, r, dst, maxBytes, true)
}

func decodeJSON(w http.ResponseWriter, r *http.Request, dst interface{}, maxBytes int64, allowEmpty bool) error {
	if maxBytes <= 0 {
		maxBytes = MaxJSONBodyBytes
	}
	if r.Body == nil {
		if allowEmpty {
			return nil
		}
		return fmt.Errorf("empty request body")
	}

	r.Body = http.MaxBytesReader(w, r.Body, maxBytes)

	dec := json.NewDecoder(r.Body)
	dec.DisallowUnknownFields()

	if err := dec.Decode(dst); err != nil {
		if allowEmpty && errors.Is(err, io.EOF) {
			return nil
		}
		return err
	}

	// Enforce exactly one JSON value: a well-formed first value
	// followed by anything other than EOF is rejected. This closes the
	// '{"a":1}{"a":2}' and '{...} trailing-garbage' cases that a single
	// Decode() silently tolerates.
	if err := dec.Decode(&struct{}{}); !errors.Is(err, io.EOF) {
		if err == nil {
			return fmt.Errorf("request body must contain a single JSON object")
		}
		return fmt.Errorf("request body must contain a single JSON object: %w", err)
	}

	return nil
}

// DecodeJSONError maps an error returned by DecodeJSONStrict /
// DecodeJSONStrictAllowEmpty to the HTTP status code and a safe,
// generic client message.
//
//   - An *http.MaxBytesError (body exceeded the cap) maps to 413
//     Request Entity Too Large.
//   - Every other decode error (malformed JSON, unknown field, wrong
//     type, trailing data, empty body) maps to 400 Bad Request.
//
// The returned message is safe to send to the client verbatim; it
// never leaks internal state beyond the decoder's own description of
// the malformed input.
func DecodeJSONError(err error) (int, string) {
	if err == nil {
		return http.StatusOK, ""
	}
	var maxErr *http.MaxBytesError
	if errors.As(err, &maxErr) {
		return http.StatusRequestEntityTooLarge,
			fmt.Sprintf("request body too large; limit is %d bytes", maxErr.Limit)
	}
	return http.StatusBadRequest, "invalid JSON: " + err.Error()
}
