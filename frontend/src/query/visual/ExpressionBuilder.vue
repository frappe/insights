<script setup>
import Code from '@/components/Controls/Code.vue'
import { fieldtypesToIcon, returnTypesToIcon } from '@/utils'
import { parse } from '@/utils/expressions'
import { FUNCTIONS } from '@/utils/query'
import { computed, nextTick, reactive, ref, watch } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: Object,
	columnOptions: Array,
})

const rawExpression = computed({
	get: () => props.modelValue?.raw || '',
	set: (value) =>
		emit('update:modelValue', {
			raw: value,
			ast: parse(value).ast,
		}),
})

const focused = ref(false)
const codeEditor = ref(null)
const functionHelp = ref(null)
const suggestionContext = reactive({
	from: null,
	to: null,
	text: null,
})
watch(rawExpression, (val) => {
	if (!val.length) {
		suggestionContext.from = null
		suggestionContext.to = null
		suggestionContext.text = null
	}
})

const codeViewUpdate = function ({ cursorPos: _cursorPos }) {
	functionHelp.value = null

	if (!rawExpression.value) {
		suggestionContext.from = null
		suggestionContext.to = null
		suggestionContext.text = null
		return
	}

	const tokens = parse(rawExpression.value).tokens
	const token = tokens
		.filter((t) => t.type == 'FUNCTION' && t.start < _cursorPos && t.end >= _cursorPos)
		.at(-1)

	if (token) {
		const { value } = token
		if (FUNCTIONS[value]) {
			functionHelp.value = FUNCTIONS[value]
		}
	}
}

function onSuggestionSelect(item) {
	const raw = rawExpression.value || ''
	const start = isNaN(suggestionContext.from)
		? codeEditor.value.cursorPos
		: suggestionContext.from
	const end = isNaN(suggestionContext.to) ? codeEditor.value.cursorPos : suggestionContext.to

	if (item.suggestionType === 'function') {
		const textBeforeToken = raw.slice(0, start)
		const textAfterToken = raw.slice(end)
		let newText = `${item.label}`
		if (!textAfterToken.trim().startsWith('(')) newText += '()'
		rawExpression.value = `${textBeforeToken}${newText}${textAfterToken}`

		const newCursorPos = start + newText.length - 1
		nextTick(() => {
			codeEditor.value.focus()
			codeEditor.value.setCursorPos(newCursorPos)
		})
	}

	if (item.suggestionType === 'column') {
		// insert `table.column`
		const textBefore = raw.slice(0, start)
		const textAfter = raw.slice(end)
		let newText = `${item.table}.${item.column}`
		if (!textBefore.trim().endsWith('`')) newText = '`' + newText
		if (!textAfter.trim().startsWith('`')) newText += '`'
		rawExpression.value = `${textBefore}${newText}${textAfter}`

		const newCursorPos = start + newText.length
		nextTick(() => {
			codeEditor.value.focus()
			codeEditor.value.setCursorPos(newCursorPos)
		})
	}
}

const allFunctionOptions = Object.keys(FUNCTIONS).map((f) => {
	return {
		label: f,
		...FUNCTIONS[f],
	}
})
const allOptions = computed(() => {
	return [
		...props.columnOptions.map((c) => ({
			...c,
			icon: fieldtypesToIcon[c.type],
			label: c.label || c.column,
			value: `${c.table}.${c.column}`,
			description: c.table_label,
			suggestionType: 'column',
		})),
		...allFunctionOptions.map((f) => ({
			icon: returnTypesToIcon[f.returnType],
			label: f.label,
			value: f.label,
			description: f.returnType,
			suggestionType: 'function',
		})),
	]
})

const filteredOptions = computed(() => {
	if (!suggestionContext.text) return allOptions.value
	const _searchTxt = suggestionContext.text.toLowerCase()
	return allOptions.value.filter(
		(o) =>
			o.label.toLowerCase().includes(_searchTxt) ||
			o.value.toLowerCase().includes(_searchTxt) ||
			o.description?.toLowerCase().includes(_searchTxt)
	)
})

const filteredGroupedOptions = computed(() => {
	return [
		{
			groupLabel: 'Columns',
			items: filteredOptions.value.filter((o) => o.suggestionType === 'column'),
		},
		{
			groupLabel: 'Functions',
			items: filteredOptions.value.filter((o) => o.suggestionType === 'function'),
		},
	]
})

const onGetCodeCompletion = (context) => {
	const _context = context.matchBefore(/\w*/)
	if (!_context) return
	suggestionContext.from = _context.from
	suggestionContext.to = _context.to
	suggestionContext.text = _context.text
}
</script>

<template>
	<div class="min-w-[32rem]">
		<span class="mb-2 block text-sm leading-4 text-gray-700">Expression</span>
		<div
			class="h-fit min-h-[2.5rem] rounded rounded-b-none border border-transparent bg-gray-100 p-0 px-1 transition-all"
			:class="
				focused ? ' border border-b-0 !border-gray-300 bg-white hover:bg-transparent' : ''
			"
		>
			<Code
				ref="codeEditor"
				v-model="rawExpression"
				:completions="onGetCodeCompletion"
				placeholder="Write an expression"
				@focus="focused = true"
				@blur="focused = false"
				@viewUpdate="codeViewUpdate"
			></Code>
		</div>
		<div
			class="-mt-1 flex h-[14rem] divide-x divide-gray-300 rounded rounded-t-none border border-t border-gray-300"
		>
			<div
				class="relative flex flex-1 flex-col overflow-hidden overflow-y-auto"
				v-auto-animate
			>
				<template v-for="group in filteredGroupedOptions">
					<div
						class="sticky top-0 flex-shrink-0 truncate bg-gray-50 px-2.5 py-1.5 text-sm font-medium text-gray-600"
					>
						{{ group.groupLabel }}
					</div>
					<div
						v-for="item in group.items.slice(0, 25)"
						:key="item.value"
						class="exp-editor-suggestion flex cursor-pointer items-center rounded py-1.5 px-2 hover:bg-gray-100"
						@click.prevent.stop="onSuggestionSelect(item)"
					>
						<component
							:is="item.icon"
							class="mr-1 h-4 w-4 flex-shrink-0 text-gray-600"
						/>
						<div class="flex flex-1 items-center justify-between overflow-hidden">
							<span class="flex-1 truncate text-sm text-gray-700">
								{{ item.label }}
							</span>
							<span
								v-if="item.description"
								class="flex-shrink-0 text-xs text-gray-500"
							>
								{{ item.description }}
							</span>
						</div>
					</div>
					<div
						v-if="group.items.length == 0"
						class="flex h-10 items-center justify-center text-sm text-gray-500"
					>
						No {{ group.groupLabel.toLowerCase() }} found
					</div>
				</template>
			</div>
			<div class="flex flex-1 flex-col overflow-hidden pb-2" v-auto-animate>
				<div
					class="flex-shrink-0 truncate bg-gray-50 px-2.5 py-1.5 text-sm font-medium text-gray-600"
				>
					Info
				</div>
				<div v-if="functionHelp" class="flex flex-col px-3 py-2 text-sm">
					<p>{{ functionHelp.description }}</p>
					<div class="mt-2 rounded bg-gray-50 p-2 text-xs leading-5">
						<code>
							<span class="text-gray-600"># Syntax</span>
							<br />
							{{ functionHelp.syntax }}
							<br />
							<br />
							<span class="text-gray-600"># Example</span>
							<br />
							{{ functionHelp.example }}
						</code>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>
