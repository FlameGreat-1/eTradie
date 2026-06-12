// executionctl is the operator CLI for the etradie execution service.
//
// Usage:
//
//	executionctl replay --user=<user_id> --since=<rfc3339> [--until=<rfc3339>] \
//	                    --addr=<host:port> --token=<service_token>
//
// The replay subcommand calls GET /internal/audit/replay on the
// execution HTTP server and prints the audit log as JSON to stdout.
// It is designed to be piped into jq for filtering:
//
//	executionctl replay --user=u-abc123 --since=2026-05-01T00:00:00Z \
//	    | jq '.[] | select(.action == "LIMIT_ORDER_PLACED")'
//
// Authentication: the --token flag must carry a valid service token
// issued by the execution service's auth.TokenService. In production,
// operators obtain this via:
//
//	kubectl -n etradie-system exec deploy/etradie-execution -- \
//	    executionctl replay --user=... --since=... --token=$(cat /var/run/secrets/service_token)
//
// Audit ref: CHECKLIST Section 7 'Replay capability (audit + debugging)'.
package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

const (
	defaultAddr    = "localhost:8080"
	defaultTimeout = 30 * time.Second
)

func main() {
	if len(os.Args) < 2 {
		fmt.Fprintf(os.Stderr, "Usage: executionctl <subcommand> [flags]\n")
		fmt.Fprintf(os.Stderr, "Subcommands: replay\n")
		os.Exit(1)
	}

	switch os.Args[1] {
	case "replay":
		os.Exit(runReplay(os.Args[2:]))
	default:
		fmt.Fprintf(os.Stderr, "Unknown subcommand: %s\n", os.Args[1])
		fmt.Fprintf(os.Stderr, "Subcommands: replay\n")
		os.Exit(1)
	}
}

func runReplay(args []string) int {
	fs := flag.NewFlagSet("replay", flag.ContinueOnError)
	fs.SetOutput(os.Stderr)

	var (
		userID = fs.String("user", "", "User ID to replay audit log for (required)")
		sinceS = fs.String("since", "", "Start timestamp in RFC3339 format (required)")
		untilS = fs.String("until", "", "End timestamp in RFC3339 format (default: now)")
		addr   = fs.String("addr", defaultAddr, "Execution HTTP server host:port")
		token  = fs.String("token", "", "Service token for authentication (required)")
		pretty = fs.Bool("pretty", false, "Pretty-print JSON output")
	)

	if err := fs.Parse(args); err != nil {
		return 1
	}

	if *userID == "" {
		fmt.Fprintln(os.Stderr, "error: --user is required")
		fs.Usage()
		return 1
	}
	if *sinceS == "" {
		fmt.Fprintln(os.Stderr, "error: --since is required (RFC3339, e.g. 2026-05-01T00:00:00Z)")
		fs.Usage()
		return 1
	}
	if _, err := time.Parse(time.RFC3339, *sinceS); err != nil {
		fmt.Fprintf(os.Stderr, "error: --since is not valid RFC3339: %v\n", err)
		return 1
	}
	if *untilS != "" {
		if _, err := time.Parse(time.RFC3339, *untilS); err != nil {
			fmt.Fprintf(os.Stderr, "error: --until is not valid RFC3339: %v\n", err)
			return 1
		}
	}
	if *token == "" {
		// Fall back to EXECUTION_SERVICE_TOKEN env var so CI scripts
		// do not need to pass the token on the command line.
		*token = strings.TrimSpace(os.Getenv("EXECUTION_SERVICE_TOKEN"))
	}
	if *token == "" {
		fmt.Fprintln(os.Stderr, "error: --token is required (or set EXECUTION_SERVICE_TOKEN env var)")
		return 1
	}

	// Build the request URL.
	base := fmt.Sprintf("http://%s/internal/audit/replay", *addr)
	params := url.Values{}
	params.Set("user_id", *userID)
	params.Set("since", *sinceS)
	if *untilS != "" {
		params.Set("until", *untilS)
	}
	fullURL := base + "?" + params.Encode()

	req, err := http.NewRequest(http.MethodGet, fullURL, nil)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: build request: %v\n", err)
		return 1
	}
	req.Header.Set("Authorization", "Bearer "+*token)
	req.Header.Set("Accept", "application/json")

	client := &http.Client{Timeout: defaultTimeout}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: HTTP request failed: %v\n", err)
		return 1
	}
	defer resp.Body.Close()

	body, err := io.ReadAll(resp.Body)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: read response body: %v\n", err)
		return 1
	}

	if resp.StatusCode != http.StatusOK {
		fmt.Fprintf(os.Stderr, "error: server returned %d: %s\n", resp.StatusCode, strings.TrimSpace(string(body)))
		return 1
	}

	if *pretty {
		// Re-indent for human readability.
		var raw interface{}
		if err := json.Unmarshal(body, &raw); err != nil {
			// Not valid JSON; print as-is.
			fmt.Println(string(body))
			return 0
		}
		indented, err := json.MarshalIndent(raw, "", "  ")
		if err != nil {
			fmt.Println(string(body))
			return 0
		}
		fmt.Println(string(indented))
	} else {
		fmt.Println(string(body))
	}

	return 0
}
