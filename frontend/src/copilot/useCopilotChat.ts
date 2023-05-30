import { safeJSONParse } from '@/utils'
import { call, createDocumentResource } from 'frappe-ui'
import { reactive } from 'vue'

/**
 * A composable for interacting with the Copilot chat.
 * Copilot is a chatbot that helps users to answer questions about their data.
 * A user has connected to their database and the tables are synced with Insights. So Copilot is able to answer questions about the data using the tables, columns and data.
 * Copilot is able to answer following type of questions:
 * - What is the average order value within the last 30 days?
 */

export default function useCopilotChat() {
	let resource: CopilotChatResource = null
	const chat: CopilotChat = reactive({
		name: '',
		title: 'New Chat',
		history: [],
		loading: false,
		sending: false,
		load,
		clear,
		sendMessage,
		createNewChat,
	})
	async function load(chat_name: string) {
		chat.loading = true
		resource = getCopilotChat(chat_name)
		await resource.get.fetch()
		chat.name = resource.doc.name
		chat.title = resource.doc.title
		chat.history = safeJSONParse(resource.doc.history) || []
		chat.loading = false
	}

	async function sendMessage(message: string) {
		const id = Math.floor(Math.random() * 1000000)
		chat.history.push({ id, role: 'user', message: message })
		chat.sending = true
		await resource.setValue.submit({
			history: JSON.stringify(chat.history),
		})
		await load(chat.name)
		chat.sending = false
	}

	async function createNewChat() {
		// creates a new chat or if a empty chat already exists, it will load that chat
		chat.loading = true
		const message = await call('insights.api.copilot.create_new_chat')
		await load(message)
		chat.loading = false
	}

	async function clear() {
		chat.history = []
		chat.sending = true
		await resource.setValue.submit({
			history: JSON.stringify(chat.history),
		})
		await load(chat.name)
		chat.sending = false
	}

	return chat
}

type CopilotChatResource = ReturnType<typeof makeCopilotChatResource>
const copilotChatCache = new Map<string, CopilotChatResource>()

function getCopilotChat(docname: string) {
	if (!copilotChatCache.has(docname)) {
		copilotChatCache.set(docname, makeCopilotChatResource(docname))
	}
	return copilotChatCache.get(docname)
}

function makeCopilotChatResource(docname: string) {
	return createDocumentResource({
		doctype: 'Insights Copilot Chat',
		name: docname,
	})
}
