package policy

lease: {
	holder: "yazi.primary" | "yazi.peer"
	epoch:  int & >=1
	requiredKinds: [
		"cd",
		"hover",
		"rename",
		"bulk",
		"@yank",
		"move",
		"trash",
		"delete",
	]
}
