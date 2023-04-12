<script setup lang="jsx">
import { markRaw, nextTick, ref, watch } from 'vue'
import ContentEditable from './ContentEditable.vue'
import TextBlock from './TextBlock.vue'
import TableBlock from './TableBlock.vue'
const title = ref('Sales Analysis')

const page = ref([
	{
		type: 'h1',
		content: 'Funnel',
	},
	{
		type: 'h2',
		content: 'Introduction',
	},
	{
		type: 'h3',
		content: '1. What is a funnel?',
	},
	{
		type: 'p',
		content:
			'A funnel is a visualization of the steps a user takes to complete a goal. It is a way to visualize the conversion rate of a user from one step to the next.',
	},
	{
		type: 'blockquote',
		content: 'Note: Funnel analysis is a very common analysis in marketing.',
	},
	{
		component: (props) => <hr class="my-4 border-gray-200" />,
	},
	{
		component: markRaw(TableBlock),
		content: [
			['Step', 'Conversion Rate'],
			['Step 1', '100%'],
			['Step 2', '50%'],
			['Step 3', '25%'],
		],
	},
])

// if content of a block changes, and there is a # at the start of the content, then
// convert the block to a h1
const onBlockChange = async (block) => {
	const tagToRegex = {
		h1: /^#\s+/,
		h2: /^##\s+/,
		h3: /^###\s+/,
		blockquote: /^>\s+/,
	}
	for (const [tag, regex] of Object.entries(tagToRegex)) {
		if (regex.test(block.content)) {
			block.type = tag
			block.content = block.content.replace(regex, '')
			await nextTick()
			return
		}
	}
}

watch(
	page,
	(newPage) => {
		newPage.forEach(onBlockChange)
	},
	{ deep: true }
)

const blocks = ref()
const focus = (index) => {
	blocks.value[index].focus()
}

const addNewBlock = (index, event) => {
	event.preventDefault()
	page.value.splice(index + 1, 0, {
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
	<div class="h-full w-full border text-base">
		<div class="mx-auto mt-24 h-full w-[45rem]">
			<ContentEditable class="text-[36px] font-bold" v-model="title"></ContentEditable>

			<transition-group name="fade">
				<div v-for="(block, index) in page" :key="index" class="w-full">
					<TextBlock
						v-if="!block.component"
						ref="blocks"
						:block="block"
						@keydown.enter.exact="addNewBlock(index, $event)"
						@keydown.backspace.exact="removeBlock(index, $event)"
						@keydown.up.exact="focusPreviousBlock(index, $event)"
						@keydown.down.exact="focusNextBlock(index, $event)"
					></TextBlock>
					<component
						v-else
						ref="blocks"
						:is="block.component"
						:block="block"
						@keydown.enter.exact="addNewBlock(index, $event)"
						@keydown.backspace.exact="removeBlock(index, $event)"
						@keydown.up.exact="focusPreviousBlock(index, $event)"
						@keydown.down.exact="focusNextBlock(index, $event)"
					></component>
				</div>
			</transition-group>
		</div>
	</div>
</template>
