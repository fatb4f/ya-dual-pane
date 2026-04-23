package schema

#Outcome: {
	decision: "commit" | "reject" | "ignore"
	reason: string & != ""
	error?: string & != ""
	wire: #DdsEnvelope | null
	meta: #AuthorityMeta | null
	state: {
		leaseHolder: string
		leaseEpoch:  int & >=0
		commitSeq:   int & >=0
	} | null
}
