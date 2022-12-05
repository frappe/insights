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
	<div class="relative flex h-full w-full items-center">
		<div @dblclick="dashboard.editingLayout && (editMarkdown = true)" class="w-full">
			<TextEditor
				editor-class="h-fit prose-sm flex flex-col justify-end"
				:content="markdown"
				:editable="false"
			/>
		</div>

		<teleport :to="`#dashboard-item-actions-${item.name}`">
			<div
				v-if="dashboard.editingLayout"
				class="cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100"
			>
				<FeatherIcon
					name="edit"
					class="h-4 w-4"
					@mousedown.prevent.stop=""
					@click="editMarkdown = !editMarkdown"
				/>
			</div>
		</teleport>

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

<style lang="scss">
.prose-sm {
	& > h1,
	& > h2,
	& > h3,
	& > h4,
	& > h5,
	& > h6 {
		@apply my-1;
	}
}
</style>
