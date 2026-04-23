package schema

#DdsEnvelope: {
	kind: string & != ""
	receiver: string & != ""
	sender: string & != ""
	body: _
}

#BuiltinKind: "cd" | "hover" | "rename" | "bulk" | "@yank" | "move" | "trash" | "delete" | "hi" | "hey" | "bye"
