<script setup lang="ts">
import Code from '@/components/Controls/Code.vue'
import { call, debounce } from 'frappe-ui'
import { nextTick, ref } from 'vue'
import { DropdownOption, ColumnOption } from '../../types/query.types'

const props = defineProps<{ columnOptions: ColumnOption[] }>()
const expression = defineModel<string>({
	required: true,
})

type AutocompletionType = 'column' | 'function'
type AutocompleteOption = DropdownOption & {
	type: AutocompletionType
	from: number
	to: number
}
const autocompleteOptions = ref<AutocompleteOption[]>([])

const functionList = ref<string[]>([])
call('insights.insights.doctype.insights_data_source_v3.ibis_functions.get_function_list').then(
	(res: any) => {
		functionList.value = res
	}
)

function onViewUpdate({
	cursorPos,
	syntaxTree,
	state,
}: {
	cursorPos: number
	syntaxTree: any
	state: any
}) {
	const word = state.doc.text.at(-1).match(/\w+/g)?.at(-1) || ''
	const nodeBefore = syntaxTree.resolveInner(cursorPos, -1)

	autocompleteOptions.value = []
	let columnMatches: AutocompleteOption[] = []
	let functionMatches: AutocompleteOption[] = []

	if (nodeBefore.name === 'VariableName') {
		columnMatches = getColumnMatches(word, cursorPos)
		functionMatches = getFunctionMatches(word, cursorPos)
	} else if (nodeBefore.name) {
		columnMatches = getColumnMatches(nodeBefore.name, cursorPos)
		functionMatches = getFunctionMatches(nodeBefore.name, cursorPos)
	}

	autocompleteOptions.value = [...columnMatches, ...functionMatches]

	if (autocompleteOptions.value.length === 1 && word === autocompleteOptions.value[0].value) {
		// If there is only one match and it is the same as the word, clear the help options
		autocompleteOptions.value = []
	}

	setHelpTooltipPosition()
}

function getColumnMatches(word: string, cursorPos: number) {
	return props.columnOptions
		.filter((c) => c.value.includes(word))
		.map((c) => ({
			label: c.value,
			value: c.value,
			from: cursorPos - word.length,
			to: cursorPos,
			type: 'column' as AutocompletionType,
		}))
}

function getFunctionMatches(word: string, cursorPos: number) {
	return functionList.value
		.filter((f) => f.includes(word))
		.map((f) => ({
			label: f,
			value: f,
			from: cursorPos - word.length,
			to: cursorPos,
			type: 'function' as AutocompletionType,
		}))
}

const codeEditor = ref(null)
function autocomplete(option: AutocompleteOption) {
	const exp = expression.value
	const start = option.from
	const end = option.to

	const textBefore = exp.slice(0, start)
	const textAfter = exp.slice(end)

	let newText = `${option.label}`
	const shouldInsertParenthesis = option.type === 'function' && !textAfter.trim().startsWith('(')
	if (shouldInsertParenthesis) {
		newText += '()'
	}

	expression.value = `${textBefore}${newText}${textAfter}`

	let newCursorPos = start + newText.length
	if (shouldInsertParenthesis) {
		newCursorPos -= 1
	}
	if (!shouldInsertParenthesis) {
		newCursorPos += 1
	}
	nextTick(() => {
		const editor = codeEditor.value as any
		editor.focus()
		editor.setCursorPos(newCursorPos)
	})

	autocompleteOptions.value = []
}

const help = ref<HTMLElement>()
const codeContainer = ref<HTMLElement>()
function _setHelpTooltipPosition() {
	const helpTooltip = help.value
	const container = codeContainer.value
	if (!helpTooltip || !container) return

	const cursor = container.querySelector('.cm-cursor') as HTMLElement
	anchorElement(cursor, helpTooltip)
}
const setHelpTooltipPosition = debounce(_setHelpTooltipPosition, 100)

function anchorElement(anchor: HTMLElement, element: HTMLElement, topOffset = 4) {
	const anchorRect = anchor.getBoundingClientRect()
	element.style.position = 'absolute'
	element.style.top = `${anchorRect.top + anchorRect.height + topOffset}px`
	element.style.left = `${anchorRect.left}px`
}
</script>

<template>
	<div
		ref="codeContainer"
		class="flex max-h-[14rem] w-full overflow-scroll rounded border text-base"
	>
		<Code
			ref="codeEditor"
			language="python"
			class="column-expression"
			v-model="expression"
			@viewUpdate="onViewUpdate"
			:disable-autocompletions="true"
		></Code>
		<Teleport to="body">
			<div
				ref="help"
				v-show="autocompleteOptions.length"
				class="absolute z-[10000] max-h-[10rem] overflow-y-scroll rounded bg-white p-1 text-base shadow-lg transition-all"
			>
				<ul class="flex flex-col font-mono text-sm">
					<li
						v-for="option in autocompleteOptions"
						:key="option.value"
						@click.prevent.stop="autocomplete(option)"
					>
						<div
							class="flex cursor-pointer items-center justify-between gap-4 rounded px-2 py-1 hover:bg-gray-100"
						>
							<div>{{ option.label }}</div>
							<div class="text-gray-500">{{ option.type }}</div>
						</div>
					</li>
				</ul>
			</div>
		</Teleport>
	</div>
</template>

<style lang="scss">
.column-expression {
	.cm-content {
		height: 14rem !important;
	}
	.cm-gutters {
		height: 14rem !important;
	}
	.cm-tooltip-autocomplete {
		// position: absolute !important;
		// z-index: 1000 !important;
		display: none !important;
	}
}
</style>
