package schema

#DdsBody: _

#DdsEnvelope: {
	kind: string & != ""
	receiver: string & != ""
	sender: string & != ""
	// Opaque payload. Raw string bodies are preserved, and JSON values
	// are passed through unchanged by the bridge/runtime.
	body: #DdsBody
}

#BuiltinKind: "cd" | "hover" | "rename" | "bulk" | "@yank" | "move" | "trash" | "delete" | "hi" | "hey" | "bye"
