package querybuilder

// Exported wrappers for map access helpers used by the routing package.
// These avoid duplicating the map access logic across packages.

// GetSliceOfMapsExported is the exported version of getSliceOfMaps.
func GetSliceOfMapsExported(m map[string]interface{}, key string) []map[string]interface{} {
	return getSliceOfMaps(m, key)
}

// GetStrDefaultExported is the exported version of getStrDefault.
func GetStrDefaultExported(m map[string]interface{}, key, def string) string {
	return getStrDefault(m, key, def)
}
