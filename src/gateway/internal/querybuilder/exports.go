package querybuilder

// This file exports map access helpers for use by the routing/guards package.
//
// WHY: The guard evaluator (routing/guards.go) needs to parse calendar events
// from macro result maps using the same logic as the query builder. Rather than
// duplicating the map access functions across packages, we export thin wrappers
// here. The canonical implementations live in macro_extractor.go.
//
// CONSUMERS: routing/guards.go (checkNewsProximity)

// GetSliceOfMapsExported extracts a []map[string]interface{} from a parent map.
// Used by guards to iterate calendar events from macro result data.
func GetSliceOfMapsExported(m map[string]interface{}, key string) []map[string]interface{} {
	return getSliceOfMaps(m, key)
}

// GetStrDefaultExported extracts a string from a map with a default fallback.
// Used by guards to read event fields (impact, event_name, event_time).
func GetStrDefaultExported(m map[string]interface{}, key, def string) string {
	return getStrDefault(m, key, def)
}
