<script setup lang="ts">
import { debounce } from 'frappe-ui'
import { nextTick, ref } from 'vue'
import Code from '../../components/Code.vue'
import { fetchCall } from '../../helpers'
import { ColumnOption } from '../../types/query.types'

const props = defineProps<{ columnOptions: ColumnOption[]; placeholder?: string }>()
const expression = defineModel<string>({
	required: true,
})

const codeContainer = ref<HTMLElement | null>(null)
const suggestionElement = ref<HTMLElement | null>(null)
const cursorElementClass = '.cm-cursor.cm-cursor-primary'

type Completion = {
	name: string
	type: string
	completion: string
}
const completions = ref<Completion[]>([])
type FunctionSignature = {
	name: string
	definition: string
	description: string
	current_param: string
	current_param_description: string
	params: { name: string; description: string }[]
}
const currentFunctionSignature = ref<FunctionSignature>()
const fetchCompletions = debounce((args: any) => {
	const cursor_pos = args.cursorPos
	let code = expression.value
	code = code.slice(0, cursor_pos) + '|' + code.slice(cursor_pos)

	fetchCall('insights.insights.doctype.insights_data_source_v3.ibis.utils.get_code_completions', {
		code,
		columns: props.columnOptions.map((column) => column.label),
	})
		.then((res: any) => {
			completions.value = res.completions
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
}, 500)

function setSuggestionElementPosition() {
	// get left & top positions of the cursor
	// set the suggestion element to that position
	setTimeout(() => {
		const containerRect = codeContainer.value?.getBoundingClientRect()
		const cursorElement = codeContainer.value?.querySelector(cursorElementClass)
		const cursorRect = cursorElement?.getBoundingClientRect()

		if (cursorRect && containerRect) {
			let left = cursorRect.left
			let top = cursorRect.top + 20
			if (left <= 0 || top <= 0) {
				return
			}
			suggestionElement.value!.style.left = `${left}px`
			suggestionElement.value!.style.top = `${top}px`
		}
	}, 100)
}

const codeEditor = ref<any>(null)
function applyCompletion(completion: any) {
	const currentCursorPos = codeEditor.value.cursorPos
	const expressionValue = expression.value
	const newExpressionValue =
		expressionValue.slice(0, currentCursorPos) +
		completion.completion +
		expressionValue.slice(currentCursorPos)
	expression.value = newExpressionValue

	codeEditor.value.focus()
	let newCursorPos = codeEditor.value.cursorPos + completion.completion.length
	if (completion.type === 'function') {
		newCursorPos -= 1
	}
	nextTick(() => {
		codeEditor.value.setCursorPos(newCursorPos)
	})
}
</script>

<template>
	<div
		ref="codeContainer"
		class="relative flex h-[14rem] w-full overflow-scroll rounded border text-base"
	>
		<Code
			ref="codeEditor"
			language="python"
			class="column-expression"
			v-model="expression"
			:placeholder="placeholder"
			:completions="() => undefined"
			@view-update="
				(args) => {
					fetchCompletions(args), setSuggestionElementPosition()
				}
			"
		></Code>

		<Teleport to="body">
			<div
				ref="suggestionElement"
				class="absolute z-10 mt-1 h-fit max-h-[14rem] min-w-[14rem] max-w-[26rem] overflow-y-auto rounded-lg bg-white p-1.5 shadow-2xl transition-all"
				:class="completions.length || currentFunctionSignature ? 'block' : 'hidden'"
			>
				<div v-if="currentFunctionSignature?.description" class="flex flex-col gap-2">
					<p
						v-if="currentFunctionSignature.definition"
						v-html="currentFunctionSignature.definition"
						class="font-mono text-p-sm text-gray-700"
					></p>
					<hr v-if="currentFunctionSignature.definition" />
					<div class="whitespace-pre-wrap font-mono text-p-sm text-gray-700">
						{{ currentFunctionSignature.description }}
					</div>
				</div>

				<div v-else class="relative">
					<ul>
						<li
							class="flex h-7 cursor-pointer items-center justify-between rounded px-2.5 text-base hover:bg-gray-100"
							v-for="completion in completions"
							:key="completion.name"
							@click.prevent.stop="applyCompletion(completion)"
						>
							<span class="flex-[2] truncate">{{ completion.name }}</span>
							<span class="flex-1 truncate text-right text-sm text-gray-600">
								{{ completion.type }}
							</span>
						</li>
					</ul>
				</div>
			</div>
		</Teleport>
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
