<template>
	<Dialog :options="{ title: 'Text to SQL' }" v-model="show" :dismissable="false">
		<template #body-content>
			<div
				class="group relative mb-4 flex items-center rounded-md border border-gray-100 p-2 text-base"
				v-for="(entry, index) in chat"
				:key="index"
				:class="{
					'mr-12 bg-gray-100 pr-10': entry.role === 'assistant',
					'ml-12 bg-blue-50': entry.role === 'user',
				}"
			>
				{{ entry.content }}

				<Button
					v-if="entry.role === 'assistant'"
					icon="share"
					appearance="minimal"
					class="invisible absolute right-2 group-hover:visible"
					@click="setSQL(entry.content)"
				>
				</Button>
			</div>

			<div v-if="generate_sql.loading" class="mb-4 flex text-sm">Generating query...</div>

			<textarea
				class="form-input my-2 w-full p-2.5 pl-3 text-base placeholder:text-gray-500"
				v-model="newPrompt"
				placeholder="Ask a question..."
			></textarea>

			<div class="flex justify-end space-x-2">
				<Button @click="chat = []"> Clear </Button>
				<Button appearance="primary" @click="reply" :loading="generate_sql.loading">
					Send
				</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { createResource } from 'frappe-ui'
import { computed, ref, inject } from 'vue'

const emit = defineEmits(['update:show'])
const props = defineProps({
	show: Boolean,
	dataSource: String,
})
const show = computed({
	get: () => props.show,
	set: (value) => {
		emit('update:show', value)
	},
})

const query = inject('query')
const chat = ref([])
const newPrompt = ref('')

const generate_sql = createResource({ url: 'insights.api.chat_bot_ai.generate_sql' })
function reply() {
	if (!newPrompt.value) return
	if (generate_sql.loading) return

	generate_sql
		.submit({
			prompt: newPrompt.value,
			data_source: props.dataSource,
			chat_history: chat.value,
		})
		.then((response) => {
			chat.value.push({
				role: 'assistant',
				content: response,
			})
		})

	chat.value.push({
		role: 'user',
		content: newPrompt.value,
	})
	newPrompt.value = ''
}

function setSQL(sql) {
	emit('update:show', false)
	query.setValue.submit({ sql })
}
</script>
