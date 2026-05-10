package paddle

import (
	"crypto/hmac"
	"crypto/sha256"
	"encoding/hex"
	"fmt"
	"net/http"
	"strings"
)

// VerifyWebhookSignature verifies the incoming Paddle webhook signature.
// It splits the signature header into ts and h1 components and verifies the HMAC.
func VerifyWebhookSignature(r *http.Request, body []byte, secretKey string) error {
	sigHeader := r.Header.Get("Paddle-Signature")
	if sigHeader == "" {
		return fmt.Errorf("missing Paddle-Signature header")
	}

	parts := strings.Split(sigHeader, ";")
	var ts, h1 string
	for _, part := range parts {
		kv := strings.SplitN(part, "=", 2)
		if len(kv) != 2 {
			continue
		}
		switch kv[0] {
		case "ts":
			ts = kv[1]
		case "h1":
			h1 = kv[1]
		}
	}

	if ts == "" || h1 == "" {
		return fmt.Errorf("invalid signature format")
	}

	payload := fmt.Sprintf("%s:%s", ts, string(body))
	
	mac := hmac.New(sha256.New, []byte(secretKey))
	mac.Write([]byte(payload))
	expectedSignature := hex.EncodeToString(mac.Sum(nil))

	if !hmac.Equal([]byte(h1), []byte(expectedSignature)) {
		return fmt.Errorf("signature verification failed")
	}

	return nil
}
