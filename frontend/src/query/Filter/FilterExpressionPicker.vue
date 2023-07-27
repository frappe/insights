<template>
	<div class="flex flex-col">
		<!-- Expression Code Field -->
		<div class="flex justify-between">
			<div class="mb-1 text-sm font-light">Expression</div>
			<Tooltip v-if="expression.error" :text="expression.error">
				<div class="!mt-1 flex cursor-pointer items-center text-xs text-red-500">
					<FeatherIcon name="alert-circle" class="h-4 w-4" />
				</div>
			</Tooltip>
		</div>
		<Popover class="h-36 w-full text-sm" placement="left-start">
			<template #target="{ open }">
				<div class="relative h-full w-full rounded border p-1">
					<Code
						v-model="input"
						:completions="getCompletions"
						@inputChange="open"
						@viewUpdate="codeViewUpdate"
					></Code>
					<ExpressionHelpDialog />
				</div>
			</template>
			<template #body>
				<div class="w-full pr-3 text-base">
					<transition
						enter-active-class="transition duration-100 ease-out"
						enter-from-class="transform scale-95 opacity-0"
						enter-to-class="transform scale-100 opacity-100"
						leave-active-class="transition duration-75 ease-in"
						leave-from-class="transform scale-100 opacity-100"
						leave-to-class="transform scale-95 opacity-0"
					>
						<div
							v-show="expression.help"
							class="ml-auto w-[20rem] rounded border bg-white p-2 shadow-lg"
						>
							<span class="mr-1 font-light">Syntax:</span>
							<span class="font-medium italic" style="font-family: 'Fira Code'">
								{{ expression.help?.syntax }}
							</span>
							<br />
							<br />
							<span>{{ expression.help?.description }}</span>
							<br />
							<br />
							<span class="mr-1 font-light">Example:</span>
							<span class="font-medium" style="font-family: 'Fira Code'">
								{{ expression.help?.example }}
							</span>
						</div>
					</transition>
				</div>
			</template>
		</Popover>

		<!-- Action Buttons -->
		<div class="mt-3 flex justify-end space-x-2">
			<Button
				variant="solid"
				@click="addExpressionFilter"
				:disabled="Boolean(expression.error)"
			>
				{{ editing ? 'Update' : 'Add ' }}
			</Button>
		</div>
	</div>
</template>

<script setup>
import Code from '@/components/Controls/Code.vue'
import ExpressionHelpDialog from '../ExpressionHelpDialog.vue'
import Tooltip from '@/components/Tooltip.vue'
import { debounce } from 'frappe-ui'

import { FUNCTIONS } from '@/utils/query'
import { parse } from '@/utils/expressions'
import { inject, watchEffect, reactive, ref, computed } from 'vue'

const query = inject('query')

const emit = defineEmits(['filter-select', 'close'])
const props = defineProps({
	filter: {
		type: Object,
		default: {},
	},
})
const editing = computed(() => query.filters.editFilterAt.idx !== -1)
const input = ref(props.filter?.raw || '')

// parse the expression when input changes
const expression = reactive({
	raw: input.value,
	ast: null,
	error: null,
	tokens: [],
	help: null,
})
watchEffect(() => {
	expression.raw = input.value
	const { ast, tokens, errorMessage } = parse(expression.raw)
	expression.ast = ast
	expression.tokens = tokens
	expression.error = errorMessage
})

const getCompletions = (context, syntaxTree) => {
	let word = context.matchBefore(/\w*/)
	let nodeBefore = syntaxTree.resolveInner(context.pos, -1)

	if (nodeBefore.name === 'TemplateString') {
		return {
			from: word.from,
			options: query.columns.options.map((c) => {
				return { label: `${c.table}.${c.column}` }
			}),
		}
	}
	if (nodeBefore.name === 'VariableName') {
		return {
			from: word.from,
			options: Object.keys(FUNCTIONS).map((label) => ({ label })),
		}
	}
}

const codeViewUpdate = debounce(function ({ cursorPos }) {
	expression.help = null

	const { tokens } = expression
	const token = tokens
		.filter((t) => t.start <= cursorPos - 1 && t.end >= cursorPos && t.type == 'FUNCTION')
		.at(-1)
	if (token) {
		const { value } = token
		if (FUNCTIONS[value]) {
			expression.help = FUNCTIONS[value]
		}
	}
}, 300)

const addExpressionFilter = () => {
	emit('filter-select', {
		...expression.ast,
		raw: expression.raw,
		is_expression: true,
	})
}
</script>
