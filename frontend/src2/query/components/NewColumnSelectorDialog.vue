<script setup lang="ts">
import Code from '@/components/Controls/Code.vue'
import { COLUMN_TYPES } from '@/utils'
import { call, debounce } from 'frappe-ui'
import { computed, nextTick, ref } from 'vue'
import { ColumnDataType, ColumnOption, DropdownOption, MutateArgs } from '../../types/query.types'
import { expression } from '../helpers'

const props = defineProps<{ mutation?: MutateArgs; columnOptions: ColumnOption[] }>()
const emit = defineEmits({ select: (column: MutateArgs) => true })
const showDialog = defineModel()

const columnTypes = COLUMN_TYPES.map((t) => t.value as ColumnDataType)

const newColumn = ref(
	props.mutation
		? {
				name: props.mutation.new_name,
				type: props.mutation.data_type,
				expression: props.mutation.expression.expression,
		  }
		: {
				name: 'new_column',
				type: columnTypes[0],
				expression: '',
		  }
)

const isValid = computed(() => {
	return newColumn.value.name && newColumn.value.type && newColumn.value.expression.trim()
})

function confirmCalculation() {
	if (!isValid.value) return
	emit('select', {
		new_name: newColumn.value.name,
		data_type: newColumn.value.type,
		expression: expression(newColumn.value.expression),
	})
	resetNewColumn()
	showDialog.value = false
}
function resetNewColumn() {
	newColumn.value = {
		name: 'New Column',
		type: columnTypes[0],
		expression: '',
	}
}

type AutocompletionType = 'column' | 'function'
type AutocompleteOption = DropdownOption & {
	type: AutocompletionType
	from: number
	to: number
}
const helpOptions = ref<AutocompleteOption[]>([])
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
	const word = state.doc.text.join(' ').match(/\w+/g)?.at(-1) || ''
	const nodeBefore = syntaxTree.resolveInner(cursorPos, -1)

	helpOptions.value = []
	let columnMatches: AutocompleteOption[] = []
	let functionMatches: AutocompleteOption[] = []

	if (nodeBefore.name === 'VariableName') {
		columnMatches = props.columnOptions
			.filter((c) => c.value.includes(word))
			.map((c) => ({
				label: c.value,
				value: c.value,
				from: cursorPos - word.length,
				to: cursorPos,
				type: 'column' as AutocompletionType,
			}))
		functionMatches = functionList.value
			.filter((f) => f.includes(word))
			.map((f) => ({
				label: f,
				value: f,
				from: cursorPos - word.length,
				to: cursorPos,
				type: 'function' as AutocompletionType,
			}))
	} else if (nodeBefore.name) {
		columnMatches = props.columnOptions
			.filter((c) => c.value.includes(nodeBefore.name))
			.map((c) => ({
				label: c.value,
				value: c.value,
				from: cursorPos - nodeBefore.name.length,
				to: cursorPos,
				type: 'column' as AutocompletionType,
			}))
		functionMatches = functionList.value
			.filter((f) => f.includes(nodeBefore.name))
			.map((f) => ({
				label: f,
				value: f,
				from: cursorPos - nodeBefore.name.length,
				to: cursorPos,
				type: 'function' as AutocompletionType,
			}))
	}

	helpOptions.value = [...columnMatches, ...functionMatches]

	setHelpTooltipPosition()
}

function autocomplete(option: AutocompleteOption) {
	const expression = newColumn.value.expression
	const start = option.from
	const end = option.to

	const textBefore = expression.slice(0, start)
	const textAfter = expression.slice(end)
	let newText = `${option.label}`
	if (option.type === 'function' && !textAfter.trim().startsWith('(')) {
		newText += '()'
	}
	newColumn.value.expression = `${textBefore}${newText}${textAfter}`

	let newCursorPos = start + newText.length
	if (option.type === 'function' && !textAfter.trim().startsWith('(')) {
		newCursorPos -= 1
	}
	if (option.type === 'function' && textAfter.trim().startsWith('(')) {
		newCursorPos += 1
	}
	nextTick(() => {
		codeEditor.value?.focus()
		codeEditor.value?.setCursorPos(newCursorPos)
	})

	helpOptions.value = []
}

const help = ref(null)
const codeContainer = ref(null)
const codeEditor = ref(null)
const setHelpTooltipPosition = debounce(async () => {
	if (codeContainer.value && help.value) {
		const helpTooltip = help.value as HTMLElement
		const container = codeContainer.value as HTMLElement
		const cursor = container.querySelector('.cm-cursor') as HTMLElement

		const cursorRect = cursor.getBoundingClientRect()
		if (cursorRect.top) {
			helpTooltip.style.display = 'block'
			helpTooltip.style.top = `${cursorRect.top + cursorRect.height + 4}px`
			helpTooltip.style.left = `${cursorRect.left}px`
		} else {
			helpTooltip.style.display = 'none'
		}
	}
}, 100)
</script>

<template>
	<Dialog
		:modelValue="showDialog"
		@after-leave="resetNewColumn"
		@close="!newColumn.expression && (showDialog = false)"
	>
		<template #body>
			<div class="bg-white px-4 pb-6 pt-5 sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Create Column</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md">
					</Button>
				</div>
				<div class="flex flex-col gap-2">
					<div
						ref="codeContainer"
						class="flex max-h-[14rem] w-full overflow-scroll rounded border text-base"
					>
						<Code
							ref="codeEditor"
							language="python"
							class="column-expression"
							v-model="newColumn.expression"
							:disable-autocompletions="true"
							@viewUpdate="onViewUpdate"
						></Code>
						<Teleport to="body">
							<div
								ref="help"
								v-show="helpOptions.length"
								class="absolute z-[10000] max-h-[10rem] overflow-y-scroll rounded bg-white p-1 text-base shadow-lg transition-all"
							>
								<ul class="flex flex-col font-mono text-sm">
									<li
										v-for="option in helpOptions"
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
					<div class="flex gap-2">
						<FormControl
							type="text"
							class="flex-1"
							label="Column Name"
							autocomplete="off"
							placeholder="Column Name"
							v-model="newColumn.name"
						/>
						<FormControl
							type="select"
							class="flex-1"
							label="Column Type"
							autocomplete="off"
							:options="columnTypes"
							v-model="newColumn.type"
						/>
					</div>
				</div>
				<div class="mt-2 flex items-center justify-between gap-2">
					<div></div>
					<div class="flex items-center gap-2">
						<Button
							label="Confirm"
							variant="solid"
							:disabled="!isValid"
							@click="confirmCalculation"
						/>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
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
