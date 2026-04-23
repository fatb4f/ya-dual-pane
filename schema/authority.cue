package schema

#AuthorityMeta: {
	eventId: string & != ""
	originSeq: int & >=0
	leaseEpoch: int & >=0
	participantId?: string & != ""
	commitSeq?: int & >=0
	causalId?: string & != ""
	decision?: "commit" | "reject" | "ignore"
}

#Ingress: {
	wire: #DdsEnvelope
	meta: #AuthorityMeta
}
