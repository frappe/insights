<script setup>
import { Dialog, TextEditor } from 'frappe-ui'
import { ref, inject, watch, nextTick } from 'vue'
const props = defineProps({
	item: {
		type: Object,
		required: true,
	},
})

const markdown = ref({ ...props.item }.markdown)

const textEditor = ref(null)
const editMarkdown = ref(false)
watch(editMarkdown, (value) => {
	value &&
		setTimeout(() => {
			textEditor.value.editor.commands.focus()
		}, 0)
})

const dashboard = inject('dashboard')
function updateMarkdown() {
	dashboard.update_markdown
		.submit({
			item: { ...props.item, markdown: markdown.value },
		})
		.then(() => {
			editMarkdown.value = false
		})
}
async function discardText() {
	markdown.value = props.item.markdown
	// need to wait, for some reason, if not, then the text editor content is not updated
	await nextTick()
	editMarkdown.value = false
}
</script>

<template>
	<div class="relative h-full w-full">
		<TextEditor editor-class="min-h-[4rem] prose-sm" :content="markdown" :editable="false" />

		<div
			class="absolute top-0 right-0 flex cursor-pointer space-x-1 p-1"
			v-if="dashboard.editingLayout"
		>
			<div class="cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100">
				<FeatherIcon
					name="edit"
					class="h-3.5 w-3.5"
					@mousedown.prevent.stop=""
					@click="editMarkdown = !editMarkdown"
				/>
			</div>
			<div class="cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100">
				<FeatherIcon
					name="x"
					class="h-3.5 w-3.5"
					@mousedown.prevent.stop=""
					@click="dashboard.removeItem(props.item.name)"
				/>
			</div>
		</div>

		<Dialog
			:options="{ title: 'Edit Text' }"
			v-model="editMarkdown"
			:dismissable="true"
			@close="discardText"
		>
			<template #body-content>
				<TextEditor
					ref="textEditor"
					:content="markdown"
					:editable="editMarkdown"
					editor-class="min-h-[4rem] prose-sm cursor-text bg-gray-100 rounded-md p-2"
					@change="(val) => (markdown = val)"
				/>
			</template>
			<template #actions>
				<Button appearance="primary" @click="updateMarkdown" :disabled="!markdown">
					Save
				</Button>
				<Button @click="discardText">Discard</Button>
			</template>
		</Dialog>
	</div>
</template>
