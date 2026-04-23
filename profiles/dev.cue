package profiles

import (
	"github.com/example/ya-dual-pane/policy"
)

participants: policy.participants
lease: policy.lease & {
	holder: "yazi.primary"
	epoch:  1
}
routing: policy.routing
