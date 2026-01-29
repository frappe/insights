<script setup lang="ts">
import { debounce } from 'frappe-ui'
import { computed, onMounted, ref } from 'vue'
import Code from '../../components/Code.vue'
import { cachedCall } from '../../helpers'
import { DropdownOption } from '../../types/query.types'
import { Info, CheckCircle } from 'lucide-vue-next'
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
	class?: string
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

onMounted(() => {
	// fix clipping of tooltip & signature element because of dialog styling
	const dialogElement = codeContainer.value?.closest('.my-8.overflow-hidden.rounded-xl')
	if (!dialogElement) {
		return
	}
	dialogElement.classList.remove('overflow-hidden', 'rounded-xl', 'bg-white')
	dialogElement.children[0]?.classList.add('rounded-xl')

	if (expression.value?.trim()) {
		validateExpression()
	}
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
const lastValidatedExpression = ref<string>('')

const validateExpression = debounce(() => {
	const currentExpression = expression.value || ''

	if (currentExpression === lastValidatedExpression.value) {
		return
	}

	if (!currentExpression.trim()) {
		validationState.value = 'idle'
		validationErrors.value = []
		lastValidatedExpression.value = ''
		return
	}

	validationState.value = 'validating'
	lastValidatedExpression.value = currentExpression

	cachedCall('insights.insights.doctype.insights_data_source_v3.ibis.utils.validate_expression', {
		expression: currentExpression,
		column_options: JSON.stringify(props.columnOptions),
	})
		.then((res: any) => {
			if (currentExpression === expression.value) {
				if (res.is_valid) {
					validationState.value = 'valid'
					validationErrors.value = []
				} else {
					validationState.value = 'error'
					validationErrors.value = res.errors || []
				}
			}
		})
		.catch((e: any) => {
			console.error('Validation error:', e)
			if (currentExpression === expression.value) {
				validationState.value = 'idle'
				validationErrors.value = []
			}
		})
}, 500)
</script>

<template>
	<div class="flex flex-col gap-2">
		<div ref="codeContainer" class="relative flex h-[10rem] w-full text-base">
			<Code
				ref="codeEditor"
				language="python"
				:class="props.class"
				class="column-expression"
				v-model="expression"
				:placeholder="placeholder"
				:completions="getCompletions"
				:hide-line-numbers="props.hideLineNumbers"
				:multi-line="props.multiLine"
				:column-names="columnNames"
				:validation-errors="validationErrors"
				@view-update="fetchCompletions"
				@input-change="validateExpression"
			>
			</Code>
		</div>
		<div class="min-h-[2.5rem]">
			<transition name="fade" mode="out-in">
				<div class="flex items-center gap-4 max-h-[10%] px-3 py-2 border-t border-b">
					<template v-if="validationState === 'validating'">
						<LoadingIndicator class="h-4 w-4 text-gray-500" />
					</template>

					<template v-else-if="validationState === 'valid'">
						<CheckCircle class="h-4 w-4 text-sm text-[#7c7c7c]" />
						<div class="text-sm text-[#7c7c7c] font-medium">Valid Syntax</div>
					</template>

					<template v-else-if="validationErrors.length">
						<div class="flex items-center gap-2 text-red-800">
							<Info class="h-4 w-4 flex-shrink-0" />
							<div class="flex-1">
								<div
									v-for="(error, index) in validationErrors"
									:key="index"
									class="mb-2 last:mb-0"
								>
									<div class="text-sm text-[#7c7c7c] font-medium">
										{{ error.message }}
										{{ error!.hint }}
									</div>
								</div>
							</div>
						</div>
					</template>

					<template v-else>
						<div class="text-sm text-gray-500">No output</div>
					</template>
				</div>
			</transition>
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
		z-index: 50 !important;
	}
}
</style>
