

interface ChatMessage {
	id: any
	message: string
	role: "user" | "assistant"
}

interface CopilotChat {
	name: string
	mode: string
	title: string
	loading: boolean
	sending: boolean
	history: ChatMessage[]
	load: (chat_name: string) => void
	clear: () => void
	sendMessage: (message: string) => void
	createNewChat: () => void
}
