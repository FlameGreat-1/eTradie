package lemonsqueezy

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/http"
)

// VerifyWebhookSignature verifies the incoming LemonSqueezy webhook signature.
// LemonSqueezy passes the signature in the X-Signature header, which is an HMAC-SHA256 hex digest.
func VerifyWebhookSignature(r *http.Request, body []byte, secretKey string) error {
	sigHeader := r.Header.Get("X-Signature")
	if sigHeader == "" {
		return fmt.Errorf("missing X-Signature header")
	}

	mac := hmac.New(sha256.New, []byte(secretKey))
	mac.Write(body)
	expectedSignature := hex.EncodeToString(mac.Sum(nil))

	if !hmac.Equal([]byte(sigHeader), []byte(expectedSignature)) {
		return fmt.Errorf("signature verification failed")
	}

	return nil
}
