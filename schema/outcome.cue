package schema

#Outcome: {
	decision: "commit" | "reject" | "ignore"
	reason: string & != ""
	wire: #DdsEnvelope
	meta: #AuthorityMeta
	state: {
		leaseHolder: string
		leaseEpoch:  int & >=0
		commitSeq:   int & >=0
	}
}
