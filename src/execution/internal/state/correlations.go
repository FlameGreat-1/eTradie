package state

import (
	"strings"

	"github.com/flamegreat/etradie/src/execution/internal/constants"
)

// pairToGroups maps each symbol to the indices of its correlated groups.
var pairToGroups map[string][]int

func init() {
	pairToGroups = make(map[string][]int)
	for i, group := range constants.CorrelatedPairGroups {
		for _, pair := range group {
			norm := strings.ToUpper(pair)
			pairToGroups[norm] = append(pairToGroups[norm], i)
		}
	}
}

// CorrelatedGroupsFor returns the group indices that a symbol belongs to.
func CorrelatedGroupsFor(symbol string) []int {
	return pairToGroups[strings.ToUpper(symbol)]
}

// AreCorrelated returns true if two symbols share at least one group.
func AreCorrelated(a, b string) bool {
	groupsA := CorrelatedGroupsFor(a)
	groupsB := CorrelatedGroupsFor(b)
	for _, ga := range groupsA {
		for _, gb := range groupsB {
			if ga == gb {
				return true
			}
		}
	}
	return false
}
