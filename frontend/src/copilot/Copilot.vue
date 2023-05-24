<script setup>
import { ref } from 'vue'
import auth from '@/utils/auth'
import Sparkles from '@/components/Icons/Sparkles.vue'
import ContentEditable from '@/notebook/ContentEditable.vue'
import { TextEditor } from 'frappe-ui'
import useCopilotChat from '@/copilot/useCopilotChat'
import { useRouter } from 'vue-router'

const props = defineProps({ chat_id: String })
const chat = useCopilotChat()
props.chat_id ? await chat.load(props.chat_id) : await chat.createNewChat()

const router = useRouter()
if (!props.chat_id) {
	router.replace({
		params: { chat_id: chat.chat_id },
	})
}

const newMessageHTML = ref('')
const newMsgEditor = ref(null)
function sendMessage() {
	const newMessage = newMsgEditor.value.editor.getText()
	chat.sendMessage({
		message: newMessage,
		html: newMessageHTML.value,
	})
	newMessageHTML.value = ''
}

window.newMsgEditor = newMsgEditor
</script>
<template>
	<div class="h-full w-full bg-white px-6 py-4">
		<div class="h-full w-full bg-white py-16 text-base">
			<div class="relative mx-auto flex h-full w-[50rem] flex-col">
				<div class="flex flex-shrink-0 items-center justify-between py-4">
					<div class="flex items-center space-x-2">
						<Sparkles class="h-4 w-4 text-gray-600"></Sparkles>
						<div class="flex-1 font-medium">Insights Copilot</div>
					</div>
					<Button appearance="minimal" icon="sidebar"></Button>
				</div>
				<div class="flex-1 overflow-y-scroll pb-6">
					<div class="flex flex-col space-y-6">
						<div v-for="message in chat.history" :key="message.id" class="flex gap-4">
							<div class="flex-shrink-0" v-if="message.role === 'assistant'">
								<div
									class="flex h-8 w-8 items-center justify-center rounded-full bg-blue-50"
								>
									<Sparkles class="h-4 w-4 text-blue-500"></Sparkles>
								</div>
							</div>
							<div class="flex-shrink-0" v-else-if="message.role === 'user'">
								<Avatar
									:label="auth.user.full_name"
									:imageURL="auth.user.user_image"
									size="md"
								/>
							</div>
							<div
								class="relative flex-1 rounded-md bg-white text-base"
								:class="[
									message.role === 'assistant'
										? 'text-gray-600'
										: 'text-gray-800',
								]"
							>
								<TextEditor
									editor-class="h-fit prose-sm flex flex-col justify-end"
									:content="message.html || message.message"
									:editable="false"
								/>
							</div>
						</div>
					</div>
				</div>
				<div class="sticky bottom-0 flex flex-shrink-0 space-x-4">
					<div
						class="flex flex-1 items-start overflow-hidden rounded-md border bg-white p-2 pl-4 text-base shadow"
					>
						<div class="mr-4 flex h-full items-center">
							<Sparkles class="h-4 w-4 text-blue-500"></Sparkles>
						</div>
						<TextEditor
							ref="newMsgEditor"
							editor-class="h-fit prose-sm flex flex-col justify-end"
							:content="newMessageHTML"
							:editable="true"
							placeholder="Ask a question..."
							@change="newMessageHTML = $event"
						/>
						<div>
							<Button
								appearance="primary"
								icon="arrow-right"
								class="!rounded-full"
								:disabled="!newMessageHTML"
								@click="sendMessage"
							></Button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
