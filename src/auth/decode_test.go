package auth

import (
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
)

type decodeTarget struct {
	Name  string `json:"name"`
	Count int    `json:"count"`
}

func newDecodeRequest(body string) (*httptest.ResponseRecorder, *http.Request) {
	w := httptest.NewRecorder()
	r := httptest.NewRequest(http.MethodPost, "/", strings.NewReader(body))
	return w, r
}

func TestDecodeJSONStrict_HappyPath(t *testing.T) {
	w, r := newDecodeRequest(`{"name":"a","count":3}`)
	var dst decodeTarget
	if err := DecodeJSONStrict(w, r, &dst, 0); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if dst.Name != "a" || dst.Count != 3 {
		t.Fatalf("unexpected decode result: %+v", dst)
	}
}

func TestDecodeJSONStrict_RejectsUnknownField(t *testing.T) {
	w, r := newDecodeRequest(`{"name":"a","evil":true}`)
	var dst decodeTarget
	err := DecodeJSONStrict(w, r, &dst, 0)
	if err == nil {
		t.Fatal("expected error for unknown field")
	}
	if status, _ := DecodeJSONError(err); status != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", status)
	}
}

func TestDecodeJSONStrict_RejectsOversizeBody(t *testing.T) {
	big := `{"name":"` + strings.Repeat("x", 2048) + `"}`
	w, r := newDecodeRequest(big)
	var dst decodeTarget
	err := DecodeJSONStrict(w, r, &dst, 256)
	if err == nil {
		t.Fatal("expected error for oversize body")
	}
	if status, _ := DecodeJSONError(err); status != http.StatusRequestEntityTooLarge {
		t.Fatalf("expected 413, got %d", status)
	}
}

func TestDecodeJSONStrict_RejectsTrailingValue(t *testing.T) {
	w, r := newDecodeRequest(`{"name":"a"}{"name":"b"}`)
	var dst decodeTarget
	err := DecodeJSONStrict(w, r, &dst, 0)
	if err == nil {
		t.Fatal("expected error for trailing second value")
	}
	if status, _ := DecodeJSONError(err); status != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", status)
	}
}

func TestDecodeJSONStrict_RejectsWrongType(t *testing.T) {
	w, r := newDecodeRequest(`{"count":"not-an-int"}`)
	var dst decodeTarget
	if err := DecodeJSONStrict(w, r, &dst, 0); err == nil {
		t.Fatal("expected error for wrong-typed field")
	}
}

func TestDecodeJSONStrict_RejectsEmptyBody(t *testing.T) {
	w, r := newDecodeRequest(``)
	var dst decodeTarget
	if err := DecodeJSONStrict(w, r, &dst, 0); err == nil {
		t.Fatal("expected error for empty body under Strict")
	}
}

func TestDecodeJSONStrictAllowEmpty_AcceptsEmptyBody(t *testing.T) {
	w, r := newDecodeRequest(``)
	var dst decodeTarget
	if err := DecodeJSONStrictAllowEmpty(w, r, &dst, 0); err != nil {
		t.Fatalf("unexpected error for empty body under AllowEmpty: %v", err)
	}
	if dst.Name != "" || dst.Count != 0 {
		t.Fatalf("expected zero-value target, got %+v", dst)
	}
}

func TestDecodeJSONStrictAllowEmpty_StillValidatesNonEmpty(t *testing.T) {
	w, r := newDecodeRequest(`{"evil":true}`)
	var dst decodeTarget
	if err := DecodeJSONStrictAllowEmpty(w, r, &dst, 0); err == nil {
		t.Fatal("expected error for unknown field even under AllowEmpty")
	}
}
