package policy

routing: {
	broadcastReceiver: "0"
	selfTargetRejectKinds: [
		"reveal_in_peer",
		"cd_peer_here",
		"copy_to_peer",
		"move_to_peer",
		"send_hovered_to_peer",
		"send_selected_to_peer",
	]
	ignoreDuplicateEventIds: true
}
