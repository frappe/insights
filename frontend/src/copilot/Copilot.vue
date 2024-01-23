<script setup>
import Sparkles from '@/components/Icons/Sparkles.vue'
import useCopilotChat from '@/copilot/useCopilotChat'
import sessionStore from '@/stores/sessionStore'
import { TextEditor } from 'frappe-ui'
import { markdownToHTML } from 'frappe-ui/src/utils/markdown'
import { inject, onBeforeUnmount, onMounted, ref, watchEffect } from 'vue'
import { useRouter } from 'vue-router'

const props = defineProps({ chat_id: String })
const chat = useCopilotChat()
props.chat_id ? await chat.load(props.chat_id) : await chat.createNewChat()

const editingMessageId = ref(null)
const updatedMessage = ref('')
function isBeingEdited(message) {
	return editingMessageId.value === message.id
}

const router = useRouter()
const session = sessionStore()
if (!props.chat_id) {
	router.replace({
		params: { chat_id: chat.chat_id },
	})
}

const newMessage = ref('')
const newMsgEditor = ref(null)
function askCopilot() {
	const text = newMsgEditor.value?.editor?.getText()
	chat.sendMessage(text)
	newMessage.value = ''
}

const chatContainer = ref(null)
const observer = new ResizeObserver(() => {
	chatContainer.value.scrollTop = chatContainer.value.scrollHeight
	const preTags = chatContainer.value?.querySelectorAll('pre > code.language-sql')
})
onMounted(() => {
	observer.observe(chatContainer.value)
})

const streamOutput = ref('...')
const $socket = inject('$socket')
$socket.on('llm_stream_output', (data) => {
	if (!data) return
	if (streamOutput.value == '...') streamOutput.value = ''
	streamOutput.value += data
})
watchEffect(() => {
	if (!chat.sending) {
		streamOutput.value = '...'
	}
})
onBeforeUnmount(() => {
	$socket.off('llm_stream_output')
})
</script>

<template>
	<div class="h-full w-full bg-white px-6 py-4">
		<div class="h-full w-full bg-white py-16 text-base">
			<div class="relative mx-auto flex h-full w-[50rem] flex-col">
				<div class="flex flex-shrink-0 items-center justify-between py-4">
					<div class="flex items-center space-x-2">
						<Sparkles class="h-4 w-4 text-gray-600"></Sparkles>
						<div class="flex-1 text-lg font-medium">Insights Copilot</div>
					</div>
					<div class="flex items-center space-x-2">
						<Dropdown
							:button="{ icon: 'more-horizontal', appearance: 'minimal' }"
							:options="[
								{
									label: 'Clear Chat',
									icon: 'x-square',
									onClick: () => chat.clear(),
								},
								{
									label: 'Open Sidebar',
									icon: 'sidebar',
									onClick: () => {},
								},
							]"
						/>
					</div>
				</div>
				<div ref="chatContainer" class="flex-1 overflow-y-scroll pb-6">
					<div class="flex flex-col space-y-6 p-0.5" v-auto-animate>
						<div
							v-for="message in chat.history"
							:key="message.id"
							class="group relative flex gap-4"
						>
							<div class="flex-shrink-0" v-if="message.role === 'assistant'">
								<Avatar size="xl">
									<Sparkles class="h-4 w-4 text-blue-500"></Sparkles>
								</Avatar>
							</div>
							<div class="flex-shrink-0" v-else-if="message.role === 'user'">
								<Avatar
									size="xl"
									:label="session.user.full_name"
									:image="session.user.user_image"
								/>
							</div>
							<div
								class="relative flex-1 rounded bg-white text-base transition-all"
								:class="
									isBeingEdited(message)
										? '-ml-1.5 pl-1.5 ring-2 ring-gray-700'
										: 'ring-0 ring-transparent '
								"
							>
								<TextEditor
									editor-class="h-fit custom-prose flex flex-col justify-end max-w-full"
									:content="markdownToHTML(message.message)"
									:editable="isBeingEdited(message)"
									@change="updatedMessage = $event"
								/>
							</div>

							<div
								v-if="message.role === 'user' && !chat.sending"
								class="absolute right-0 top-0 flex h-full items-center justify-center gap-1 pr-0.5 opacity-0 transition-all group-hover:opacity-100"
							>
								<Button
									v-if="isBeingEdited(message)"
									icon="x"
									variant="outline"
									@click="editingMessageId = null"
								></Button>
								<Button
									v-if="isBeingEdited(message)"
									icon="check"
									variant="solid"
									@click="
										() => {
											chat.updateMessage(message.id, updatedMessage)
											editingMessageId = null
											updatedMessage = ''
										}
									"
								></Button>
								<Button
									v-else
									icon="edit"
									variant="subtle"
									@click="
										() => {
											editingMessageId = message.id
											updatedMessage = message.message
										}
									"
								></Button>
							</div>
						</div>

						<div v-if="chat.sending" class="flex gap-4">
							<div class="flex-shrink-0">
								<div
									class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50"
								>
									<Sparkles class="h-4 w-4 text-blue-500"></Sparkles>
								</div>
							</div>
							<div class="relative flex-1 rounded bg-white text-base">
								<TextEditor
									editor-class="h-fit custom-prose flex flex-col justify-end max-w-full"
									:content="markdownToHTML(streamOutput)"
									:editable="false"
								/>
							</div>
						</div>
					</div>
				</div>
				<div class="sticky bottom-0 flex flex-shrink-0 space-x-4">
					<div
						class="flex flex-1 items-start overflow-hidden rounded border bg-white p-2 pl-4 text-base shadow"
					>
						<div class="mr-4 flex h-full items-center">
							<Sparkles class="h-4 w-4 text-blue-500"></Sparkles>
						</div>
						<TextEditor
							ref="newMsgEditor"
							:editable="true"
							placeholder="Ask a question..."
							editor-class="h-fit flex flex-col justify-end custom-prose max-w-full"
							:content="newMessage"
							@change="newMessage = $event"
						/>
						<div class="flex h-full items-center">
							<Button
								:appearance="!newMessage ? 'minimal' : 'primary'"
								icon="arrow-right"
								:disabled="!newMessage || chat.sending"
								@click="askCopilot"
							>
							</Button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
