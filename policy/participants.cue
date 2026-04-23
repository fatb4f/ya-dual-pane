package policy

#Participant: {
	id: string & != ""
	senderIds: [...string] & len(senderIds) > 0
	roles: [...string]
	placement: "left" | "right"
}

participants: [
	{
		id:        "yazi.primary"
		senderIds: ["100"]
		roles:     ["pane", "lease-candidate"]
		placement: "left"
	},
	{
		id:        "yazi.peer"
		senderIds: ["200"]
		roles:     ["pane", "lease-candidate"]
		placement: "right"
	},
]
