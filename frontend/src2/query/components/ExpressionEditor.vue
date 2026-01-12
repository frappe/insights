<script setup lang="ts">
import { debounce } from 'frappe-ui'
import { computed, onMounted, ref } from 'vue'
import Code from '../../components/Code.vue'
import { cachedCall } from '../../helpers'
import { DropdownOption } from '../../types/query.types'
import { Check, X, Info } from 'lucide-vue-next'

type FunctionSignature = {
	name: string
	definition: string
	description: string
	current_param: string
	current_param_description: string
	params: { name: string; description: string }[]
}

const props = defineProps<{
	columnOptions: DropdownOption[]
	placeholder?: string
	hideLineNumbers?: boolean
	multiLine?: boolean
}>()
const expression = defineModel<string>({
	required: true,
})

const emit = defineEmits<{
	functionSignatureUpdate: [signature: FunctionSignature | undefined]
}>()

const functionList = ref<string[]>([])
cachedCall('insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_list').then(
	(res: any) => {
		functionList.value = res
	}
)

const columnNames = computed(() => {
	return props.columnOptions.map((c) => c.value)
})

function getCompletions(context: any, syntaxTree: any) {
	const word = context.matchBefore(/\w+/)
	const nodeBefore = syntaxTree.resolveInner(context.pos, -1)

	if (nodeBefore.name === 'VariableName') {
		const columnMatches = getColumnMatches(word.text)
		const functionMatches = getFunctionMatches(word.text)
		return {
			from: word.from,
			options: [...columnMatches, ...functionMatches],
		}
	}
	if (nodeBefore.name) {
		const columnMatches = getColumnMatches(nodeBefore.name)
		const functionMatches = getFunctionMatches(nodeBefore.name)
		return {
			from: nodeBefore.from,
			options: [...columnMatches, ...functionMatches],
		}
	}
}

function getColumnMatches(word: string) {
	return props.columnOptions
		.filter((c) => c.value.includes(word))
		.map((c) => ({
			label: c.value,
			detail: 'column',
		}))
}

function getFunctionMatches(word: string) {
	return functionList.value
		.filter((f) => f.includes(word))
		.map((f) => ({
			label: f,
			apply: `${f}()`,
			detail: 'function',
		}))
}

const codeEditor = ref<any>(null)
const codeContainer = ref<HTMLElement | null>(null)
const signatureElement = ref<HTMLElement | null>(null)

onMounted(() => {
	// fix clipping of tooltip & signature element because of dialog styling
	const dialogElement = codeContainer.value?.closest('.my-8.overflow-hidden.rounded-xl')
	if (!dialogElement) {
		return
	}
	dialogElement.classList.remove('overflow-hidden', 'rounded-xl', 'bg-white')
	dialogElement.children[0]?.classList.add('rounded-xl')
})

const currentFunctionSignature = ref<FunctionSignature>()
const columnTypesMap = ref<Record<string, string>>({})
const fetchCompletions = debounce(() => {
	if (!codeEditor.value) {
		currentFunctionSignature.value = undefined
		emit('functionSignatureUpdate', undefined)
		return
	}

	let code = expression.value
	const codeBeforeCursor = code.slice(0, codeEditor.value.cursorPos)
	const codeAfterCursor = code.slice(codeEditor.value.cursorPos)

	code = codeBeforeCursor + '|' + codeAfterCursor

	cachedCall(
		'insights.insights.doctype.insights_data_source_v3.ibis.utils.get_code_completions',
		{
			code,
			column_options: JSON.stringify(props.columnOptions),
		}
	)
		.then((res: any) => {
			currentFunctionSignature.value = res.current_function
			columnTypesMap.value = res.column_types || {}
			// if there is a current_param, then we need to update the definition
			// add <b> & underline tags before and after the current_param value in the definition
			if (currentFunctionSignature.value?.current_param) {
				const current_param = res.current_function.current_param
				const current_param_type = res.current_function.current_param_type
				const definition = res.current_function.definition
				const current_param_index = definition.indexOf(current_param)
				if (current_param_index !== -1) {
					let paramDisplay = current_param
					if (current_param_type) {
						paramDisplay = `${current_param} (${current_param_type})`
					}
					const updated_definition =
						definition.slice(0, current_param_index) +
						`<b><u>${paramDisplay}</u></b>` +
						definition.slice(current_param_index + current_param.length)
					currentFunctionSignature.value.definition = updated_definition
				}
			}
			emit('functionSignatureUpdate', currentFunctionSignature.value)
		})
		.catch((e: any) => {
			console.error(e)
		})
}, 1000)

type ValidationError = {
	line: number
	column: number
	message: string
	hint?: string
}
const validationState = ref<'idle' | 'validating' | 'valid' | 'error'>('idle')
const validationErrors = ref<ValidationError[]>([])

const validateExpression = debounce(() => {
	if (!expression.value || !expression.value.trim()) {
		validationState.value = 'idle'
		validationErrors.value = []
		return
	}

	validationState.value = 'validating'

	cachedCall('insights.insights.doctype.insights_data_source_v3.ibis.utils.validate_expression', {
		expression: expression.value,
		column_options: JSON.stringify(props.columnOptions),
	})
		.then((res: any) => {
			if (res.is_valid) {
				validationState.value = 'valid'
				validationErrors.value = []
			} else {
				validationState.value = 'error'
				validationErrors.value = res.errors || []
			}
		})
		.catch((e: any) => {
			console.error('Validation error:', e)
			validationState.value = 'idle'
			validationErrors.value = []
		})
}, 500)

function setSignatureElementPosition() {
	setTimeout(() => {
		const containerRect = codeContainer.value?.getBoundingClientRect()
		const tooltipElement = codeContainer.value?.querySelector('.cm-tooltip-autocomplete')
		const cursorElement = codeContainer.value?.querySelector('.cm-cursor.cm-cursor-primary')

		if (!containerRect) return
		if (!signatureElement.value) return

		let left = 0,
			top = 0

		if (tooltipElement) {
			const tooltipRect = tooltipElement.getBoundingClientRect()
			left = tooltipRect.left - containerRect.left
			top = tooltipRect.top + tooltipRect.height - containerRect.top + 10
		} else if (cursorElement) {
			const cursorRect = cursorElement?.getBoundingClientRect()
			left = cursorRect.left - containerRect.left
			top = cursorRect.top - containerRect.top + 20
		}

		if (left <= 0 || top <= 0) {
			return
		}

		signatureElement.value.style.left = `${left}px`
		signatureElement.value.style.top = `${top}px`
	}, 100)
}
</script>

<template>
	<div class="flex flex-col gap-2">
		<div ref="codeContainer" class="relative flex h-[14rem] w-full text-base ">
			<div class="absolute top-2 right-2 z-20">
				<LoadingIndicator
					v-if="validationState === 'validating'"
					class="h-5 w-5 text-gray-500"
				/>
				<Check v-else-if="validationState === 'valid'" class="h-5 w-5 text-green-500" />
				<X v-else-if="validationState === 'error'" class="h-5 w-5 text-red-500" />
			</div>
			<Code
				ref="codeEditor"
				language="python"
				class="column-expression"
				v-model="expression"
				:placeholder="placeholder"
				:completions="getCompletions"
				:hide-line-numbers="props.hideLineNumbers"
				:multi-line="props.multiLine"
				:column-names="columnNames"
				@view-update="
					() => (fetchCompletions(), setSignatureElementPosition(), validateExpression())
				"
			>
			</Code>
			<div
				ref="signatureElement"
				v-show="currentFunctionSignature"
				class="absolute z-10 flex h-fit max-h-[14rem] w-[25rem] flex-col gap-2 overflow-y-auto rounded-lg bg-white px-2.5 py-1.5 shadow-md transition-all"
			>
				<template v-if="currentFunctionSignature">
					<p
						v-if="currentFunctionSignature.definition"
						v-html="currentFunctionSignature.definition"
						class="font-mono text-p-sm text-gray-800"
					></p>
					<hr v-if="currentFunctionSignature.definition" />
					<div class="whitespace-pre-wrap font-mono text-p-sm text-gray-800">
						{{ currentFunctionSignature.description }}
					</div>
				</template>
			</div>
		</div>
		<div
			v-if="validationErrors.length"
			class="max-h-[10%] rounded border border-red-200 bg-red-50 px-3 py-2"
		>
			<div class="flex items-center gap-2 text-sm text-red-800">
				<Info class="h-4 w-4 flex-shrink-0" />
				<div class="flex-1">
					<div
						v-for="(error, index) in validationErrors"
						:key="index"
						class="mb-2 last:mb-0"
					>
						<div class="font-medium">
							Line {{ error.line }}, Col {{ error.column }}: {{ error.message }}
						</div>
						<div v-if="error.hint" class="mt-1 text-red-600">
							{{ error.hint }}
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<style lang="scss">
.column-expression {
	.cm-content {
		height: 100% !important;
	}
	.cm-gutters {
		height: 100% !important;
	}
	.cm-tooltip-autocomplete {
		position: absolute !important;
		z-index: 1000 !important;
	}
}
</style>
