

interface ChatMessage {
	id: any
	message: string
	role: "user" | "assistant"
}

interface CopilotChat {
	chat_id: string
	title: string
	loading: boolean
	sending: boolean
	history: ChatMessage[]
	load: (chat_id: string) => void
	clear: () => void
	sendMessage: (message: string) => void
	createNewChat: () => void
}
