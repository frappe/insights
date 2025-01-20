<script setup lang="ts">
import { debounce } from 'frappe-ui'
import { onMounted, ref } from 'vue'
import Code from '../../components/Code.vue'
import { cachedCall } from '../../helpers'
import { DropdownOption } from '../../types/query.types'

const props = defineProps<{ columnOptions: DropdownOption[]; placeholder?: string }>()
const expression = defineModel<string>({
	required: true,
})

const functionList = ref<string[]>([])
cachedCall('insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_list').then(
	(res: any) => {
		functionList.value = res
	}
)

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

type FunctionSignature = {
	name: string
	definition: string
	description: string
	current_param: string
	current_param_description: string
	params: { name: string; description: string }[]
}
const currentFunctionSignature = ref<FunctionSignature>()
const fetchCompletions = debounce(() => {
	if (!codeEditor.value) {
		currentFunctionSignature.value = undefined
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
		}
	)
		.then((res: any) => {
			currentFunctionSignature.value = res.current_function
			// if there is a current_param, then we need to update the definition
			// add <b> & underline tags before and after the current_param value in the definition
			if (currentFunctionSignature.value?.current_param) {
				const current_param = res.current_function.current_param
				const definition = res.current_function.definition
				const current_param_index = definition.indexOf(current_param)
				if (current_param_index !== -1) {
					const updated_definition =
						definition.slice(0, current_param_index) +
						`<b><u>${current_param}</u></b>` +
						definition.slice(current_param_index + current_param.length)
					currentFunctionSignature.value.definition = updated_definition
				}
			}
		})
		.catch((e: any) => {
			console.error(e)
		})
}, 1000)

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
	<div ref="codeContainer" class="relative flex h-[14rem] w-full rounded border text-base">
		<Code
			ref="codeEditor"
			language="python"
			class="column-expression"
			v-model="expression"
			:placeholder="placeholder"
			:completions="getCompletions"
			@view-update="() => (fetchCompletions(), setSignatureElementPosition())"
		></Code>

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
