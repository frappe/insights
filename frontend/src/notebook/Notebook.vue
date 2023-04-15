<script setup lang="jsx">
import { moveCaretToEnd } from '@/utils'
import { nextTick, ref, watch } from 'vue'
import ContentEditable from './ContentEditable.vue'
import TableBlock from './blocks/TableBlock.vue'
import TextBlock from './blocks/TextBlock.vue'
import AsyncQueryBlock from './blocks/query/AsyncQueryBlock.vue'

const title = ref('')
const page = ref([])

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
			focus(page.value.indexOf(block))
			return
		}
	}
}

watch(page, (newPage) => newPage.forEach(onBlockChange), { deep: true })

const currentBlockIndex = ref(null)
const blocks = ref()
const focus = (index, event) => {
	// if an input is focused, don't focus on the block as it will move the caret to the end of the input
	if (event?.target?.closest('.focusable')) return
	// when adding a new block, vue adds the block at the end of the DOM, but the index in the page array is correct
	// eg. if page contains 5 blocks, and we add a new block after the 3rd block,
	// the new block index in the page array is 3, but the block is added at the end of the DOM i.e index 5
	const blockRef = blocks.value.find(
		(block) => block.$el.getAttribute('block-id') === page.value[index].id.toString()
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
	page.value.splice(index + 1, 0, {
		id: Math.random().toString(16).slice(2),
		type: 'p',
		content: '',
	})
	nextTick(() => focusNextBlock(index, event))
}

const removeBlock = (index, event) => {
	if (page.value[index].content === '') {
		event.preventDefault()
		page.value.splice(index, 1)
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
	if (index < page.value.length - 1) focus(index + 1)
	if (index === page.value.length - 1) focus(page.value.length - 1)
}
</script>

<template>
	<div class="h-full w-full overflow-y-scroll border bg-white py-24 text-base">
		<div class="mx-auto w-[45rem]">
			<ContentEditable
				class="focusable text-[36px] font-bold"
				v-model="title"
				placeholder="Page Title"
			></ContentEditable>

			<component
				ref="blocks"
				v-for="(block, index) in page"
				:key="block.id"
				:block="block"
				:is="blockTypeToComponent[block.type]"
				:block-id="block.id"
				@click="focus(index, $event)"
				@keydown.enter.exact="keyboardEvents[block.type]?.enter(index, $event)"
				@keydown.backspace.exact="keyboardEvents[block.type]?.backspace(index, $event)"
				@keydown.up.exact="keyboardEvents[block.type]?.up(index, $event)"
				@keydown.down.exact="keyboardEvents[block.type]?.down(index, $event)"
				@remove="page.splice(index, 1)"
			></component>

			<div class="h-24" @click="addNewBlock(page.length - 1, $event)"></div>
		</div>
	</div>
</template>
