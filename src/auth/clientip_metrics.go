package auth

import (
	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promauto"
)

// CloudflareRangesFallbackTotal counts every time the Cloudflare
// ranges file-loader path falls back to the in-binary embedded list.
// A success path (file readable + at least one valid network parsed)
// does NOT increment this counter; only the abnormal cases do, so
// `increase(...) > 0` is a meaningful alert signal.
//
// Reason labels:
//   - "unreadable":     dir/file I/O error or missing files
//   - "empty":          file readable but produced 0 valid networks
//                       AND no malformed lines (truly empty file)
//   - "malformed_only": file produced 0 valid networks AND >=1
//                       malformed lines (parse error covered all input)
//
// Registered via promauto with the Prometheus default registry, the
// same pattern src/gateway/internal/observability/metrics.go uses.
// The auth package init runs once per gateway process; no duplicate-
// registration risk.
var CloudflareRangesFallbackTotal = promauto.NewCounterVec(prometheus.CounterOpts{
	Name: "auth_cloudflare_ranges_fallback_total",
	Help: "Times the gateway fell back to the embedded Cloudflare trust list because the mounted ranges dir was unreadable, empty, or malformed.",
}, []string{"reason"})
