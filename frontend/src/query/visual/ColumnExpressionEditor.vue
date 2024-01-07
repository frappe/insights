<script setup>
import Code from '@/components/Controls/Code.vue'
import { fieldtypesToIcon, returnTypesToIcon } from '@/utils'
import { parse } from '@/utils/expressions'
import { FUNCTIONS } from '@/utils/query'
import { debounce } from 'frappe-ui'
import { computed, inject, nextTick, ref } from 'vue'
import { getSelectedTables } from './useAssistedQuery'

const COLUMN_TYPES = [
	{ label: 'String', value: 'String' },
	{ label: 'Integer', value: 'Integer' },
	{ label: 'Decimal', value: 'Decimal' },
	{ label: 'Text', value: 'Text' },
	{ label: 'Datetime', value: 'Datetime' },
	{ label: 'Date', value: 'Date' },
	{ label: 'Time', value: 'Time' },
]

const assistedQuery = inject('assistedQuery')
const emit = defineEmits(['update:column'])
const props = defineProps({ column: Object })

const column = computed({
	get: () => props.column,
	set: (val) => emit('update:column', val),
})

const focused = ref(false)
const codeEditor = ref(null)
const helpInfo = ref(null)
const currentToken = ref(null)

const codeViewUpdate = debounce(function ({ cursorPos: newCurPos }) {
	currentToken.value = null
	helpInfo.value = null

	if (!column.value.expression?.raw) return

	const tokens = parse(column.value.expression.raw).tokens
	const token = tokens
		.filter((t) => t.start <= newCurPos - 1 && t.end >= newCurPos && t.type == 'FUNCTION')
		.at(-1)

	currentToken.value = token

	if (token) {
		const { value } = token
		if (FUNCTIONS[value]) {
			helpInfo.value = FUNCTIONS[value]
		}
	}
}, 100)

const filteredColumnOptions = computed(() => {
	const selectedTables = getSelectedTables(assistedQuery)
	return assistedQuery.columnOptions
		.filter((c) => selectedTables.includes(c.table))
		.filter((c) => {
			if (!currentToken.value) return true
			if (isBetweenParenthesis()) return true
			const searchTxt = currentToken.value.value.toLowerCase()
			return (
				c.column.toLowerCase().includes(searchTxt) ||
				c.label.toLowerCase().includes(searchTxt)
			)
		})
})
const allFunctionOptions = Object.keys(FUNCTIONS).map((f) => {
	return {
		label: f,
		...FUNCTIONS[f],
	}
})
const filteredFunctionOptions = computed(() => {
	if (!currentToken.value) return allFunctionOptions
	if (isBetweenParenthesis()) return allFunctionOptions
	const searchTxt = currentToken.value.value.toLowerCase()
	return allFunctionOptions.filter((f) => {
		return f.label.toLowerCase().includes(searchTxt)
	})
})

const suggestionGroups = computed(() => {
	return [
		{
			groupLabel: 'Columns',
			items: filteredColumnOptions.value.map((c) => {
				return {
					...c,
					icon: fieldtypesToIcon[c.type],
					label: c.label || c.column,
					description: c.table_label,
					suggestionType: 'column',
				}
			}),
		},
		{
			groupLabel: 'Functions',
			items: filteredFunctionOptions.value.map((f) => {
				return {
					icon: returnTypesToIcon[f.returnType],
					label: f.label,
					description: f.returnType,
					suggestionType: 'function',
				}
			}),
		},
	]
})

function onSuggestionSelect(item) {
	const raw = column.value.expression.raw
	const start = currentToken.value?.value ? currentToken.value.start : raw.length
	const end = currentToken.value?.value ? currentToken.value.end : raw.length

	if (item.suggestionType === 'function') {
		const newText = `${item.label}()`
		const newCursorPos = start + newText.length - 1
		const textBeforeToken = raw.slice(0, start)
		const textAfterToken = raw.slice(end)
		column.value.expression.raw = `${textBeforeToken}${newText}${textAfterToken}`

		nextTick(() => {
			codeEditor.value.focus()
			codeEditor.value.setCursorPos(newCursorPos)
		})
	}
	if (item.suggestionType === 'column') {
		// insert `table.column`
		const newText = '`' + `${item.table}.${item.column}` + '`'
		const newCursorPos = start + newText.length
		const textBeforeToken = raw.slice(0, start)
		const textAfterToken = raw.slice(end)
		column.value.expression.raw = `${textBeforeToken}${newText}${textAfterToken}`

		nextTick(() => {
			codeEditor.value.focus()
			codeEditor.value.setCursorPos(newCursorPos)
		})
	}
}

function isBetweenParenthesis() {
	const raw = column.value.expression?.raw
	const start = codeEditor.value?.cursorPos
	const end = codeEditor.value?.cursorPos
	if (!raw) return false
	const textBeforeCursor = raw.slice(0, start).trim()
	const textAfterCursor = raw.slice(end).trim()
	return textBeforeCursor.endsWith('(') && textAfterCursor.startsWith(')')
}
</script>

<template>
	<div class="exp-editor space-y-3 text-base">
		<div class="flex gap-3">
			<FormControl
				type="text"
				label="Label"
				class="w-full"
				v-model="column.label"
				placeholder="Label"
				autocomplete="off"
			/>
			<FormControl
				label="Type"
				type="select"
				class="w-full"
				v-model="column.type"
				:options="COLUMN_TYPES"
			/>
		</div>

		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Expression</span>
			<div
				class="h-fit min-h-[2.5rem] rounded rounded-b-none border border-transparent bg-gray-100 p-0 px-1 transition-all"
				:class="
					focused
						? ' border border-b-0 !border-gray-300 bg-white hover:bg-transparent'
						: ''
				"
			>
				<Code
					ref="codeEditor"
					:modelValue="column.expression.raw"
					:completions="() => {}"
					placeholder="Write an expression"
					@focus="focused = true"
					@blur="focused = false"
					@viewUpdate="codeViewUpdate"
					@update:modelValue="
						column.expression = {
							raw: $event,
							ast: parse($event).ast,
						}
					"
				></Code>
			</div>
			<div
				class="-mt-1 flex h-[14rem] divide-x divide-gray-300 rounded rounded-t-none border border-t border-gray-300"
			>
				<div class="relative flex flex-[2] flex-col overflow-hidden overflow-y-scroll">
					<template v-for="group in suggestionGroups">
						<div
							class="sticky top-0 flex-shrink-0 truncate bg-gray-50 px-2.5 py-1.5 text-sm font-medium text-gray-600"
						>
							{{ group.groupLabel }}
						</div>
						<div
							v-for="item in group.items.slice(0, 25)"
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
				<div class="flex flex-[3] flex-col overflow-hidden pb-2">
					<div
						class="flex-shrink-0 truncate bg-gray-50 px-2.5 py-1.5 text-sm font-medium text-gray-600"
					>
						Info
					</div>
					<div v-if="helpInfo" class="flex flex-col px-3 py-2 text-sm">
						<p>{{ helpInfo.description }}</p>
						<div class="mt-2 rounded bg-gray-50 p-2 text-xs leading-5">
							<code>
								<span class="text-gray-600"># Syntax</span>
								<br />
								{{ helpInfo.syntax }}
								<br />
								<br />
								<span class="text-gray-600"># Example</span>
								<br />
								{{ helpInfo.example }}
							</code>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style>
.exp-editor .cm-tooltip-autocomplete {
	position: absolute !important;
}
</style>
