<script setup lang="jsx">
import Breadcrumbs from '@/components/Breadcrumbs.vue'
import useNotebookPage from '@/notebook/useNotebookPage'
import { moveCaretToEnd } from '@/utils'
import { nextTick, ref, watch } from 'vue'
import ContentEditable from './ContentEditable.vue'
import TableBlock from './blocks/TableBlock.vue'
import TextBlock from './blocks/TextBlock.vue'
import AsyncQueryBlock from './blocks/query/AsyncQueryBlock.vue'
import useNotebook from '@/notebook/useNotebook'

const props = defineProps({
	notebook: String,
	page: String,
})
const page = useNotebookPage(props.page)
const notebook = useNotebook(props.notebook)

const blockTypeToComponent = {
	h1: TextBlock,
	h2: TextBlock,
	h3: TextBlock,
	p: TextBlock,
	blockquote: TextBlock,
	query: AsyncQueryBlock,
	table: TableBlock,
}

const textBlockKeyboardEvents = {
	enter: (index, event) => addNewBlock(index, event),
	backspace: (index, event) => removeBlock(index, event),
	up: (index, event) => focusPreviousBlock(index, event),
	down: (index, event) => focusNextBlock(index, event),
}
const keyboardEvents = {
	h1: textBlockKeyboardEvents,
	h2: textBlockKeyboardEvents,
	h3: textBlockKeyboardEvents,
	p: textBlockKeyboardEvents,
	blockquote: textBlockKeyboardEvents,
	table: textBlockKeyboardEvents,
}

const onBlockChange = async (block) => {
	const tagToRegex = {
		h1: /^#\s+/,
		h2: /^##\s+/,
		h3: /^###\s+/,
		blockquote: /^>\s+/,
		query: /^\/query\s+/,
		table: /^\/table\s+/,
	}
	for (const [tag, regex] of Object.entries(tagToRegex)) {
		if (regex.test(block.content)) {
			block.type = tag
			block.content = block.content.replace(regex, '')
			await nextTick()
			focus(page.doc.items.indexOf(block))
			return
		}
	}
}

watch(
	() => page.doc.items,
	(items) => items?.forEach(onBlockChange),
	{ deep: true }
)

const currentBlockIndex = ref(null)
const blocks = ref()
const focus = (index, event) => {
	// if an input is focused, don't focus on the block as it will move the caret to the end of the input
	if (event?.target?.closest('.focusable')) return
	// when adding a new block, vue adds the block at the end of the DOM, but the index in the page array is correct
	// eg. if page contains 5 blocks, and we add a new block after the 3rd block,
	// the new block index in the page array is 3, but the block is added at the end of the DOM i.e index 5
	const blockRef = blocks.value.find(
		(block) => block.$el.getAttribute('block-id') === page.doc.items[index].id.toString()
	)
	const element = blockRef?.$el
	if (!element) return (currentBlockIndex.value = index)

	const focusable = element.closest('.focusable') || element.querySelector('.focusable')
	if (!focusable) return (currentBlockIndex.value = index)

	focusable.focus()
	moveCaretToEnd(focusable)
	return (currentBlockIndex.value = index)
}
const addNewBlock = async (index, event) => {
	event.preventDefault()
	page.doc.items.splice(index + 1, 0, {
		id: Math.random().toString(16).slice(2),
		type: 'p',
		content: '',
	})
	nextTick(() => focusNextBlock(index, event))
}

const removeBlock = (index, event) => {
	if (page.doc.items[index].content === '') {
		event.preventDefault()
		page.doc.items.splice(index, 1)
		nextTick(() => focusPreviousBlock(index, event))
	}
}

const focusPreviousBlock = (index, event) => {
	event.preventDefault()
	if (index > 0) focus(index - 1)
	if (index === 0) focus(0)
}
const focusNextBlock = (index, event) => {
	event.preventDefault()
	if (index < page.doc.items.length - 1) focus(index + 1)
	if (index === page.doc.items.length - 1) focus(page.doc.items.length - 1)
}
</script>

<template>
	<div class="h-full w-full bg-white px-8 py-4">
		<Breadcrumbs
			:items="[
				{
					label: 'Notebooks',
					href: '/notebook',
				},
				{
					label: notebook.doc.title,
					href: `/notebooks/${page.doc.notebook}`,
				},
				{
					label: page.doc.title,
					href: `/notebooks/${page.doc.notebook}/${page.doc.name}`,
				},
			]"
		>
		</Breadcrumbs>
		<div v-if="page.doc.name" class="h-full w-full overflow-y-scroll bg-white py-24 text-base">
			<div class="mx-auto w-[45rem]">
				<ContentEditable
					class="focusable text-[36px] font-bold"
					v-model="page.doc.title"
					placeholder="Page Title"
				></ContentEditable>

				<component
					ref="blocks"
					v-for="(block, index) in page.doc.items"
					:key="block.id"
					:block="block"
					:is="blockTypeToComponent[block.type]"
					:block-id="block.id"
					@click="focus(index, $event)"
					@keydown.enter.exact="keyboardEvents[block.type]?.enter(index, $event)"
					@keydown.backspace.exact="keyboardEvents[block.type]?.backspace(index, $event)"
					@keydown.up.exact="keyboardEvents[block.type]?.up(index, $event)"
					@keydown.down.exact="keyboardEvents[block.type]?.down(index, $event)"
					@remove="page.doc.items.splice(index, 1)"
				></component>

				<div
					class="h-24 cursor-text"
					@click="addNewBlock(page.doc.items.length - 1, $event)"
				></div>
			</div>
		</div>
	</div>
</template>
