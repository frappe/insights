<script setup>
import Code from '@/components/Controls/Code.vue'
import UsePopover from '@/components/UsePopover.vue'
import { parse } from '@/utils/expressions'
import { FUNCTIONS } from '@/utils/query'
import { debounce } from 'frappe-ui'
import { computed, inject, onMounted, ref } from 'vue'

const query = inject('query')
const emit = defineEmits(['update:column'])
const props = defineProps({ column: Object })

const expressionColumn = ref({
	label: props.column.label ?? '',
	type: props.column.type ?? 'String',
	expression: {
		raw: props.column.expression.raw ?? '',
		ast: props.column.expression.ast ?? null,
	},
})

const focused = ref(false)
const columnOptions = ref([])
query.getTablesColumns().then((columns) => {
	columnOptions.value = columns.map((c) => {
		return { label: `${c.table}.${c.column}` }
	})
})
const getCompletions = (context, syntaxTree) => {
	let word = context.matchBefore(/\w*/)
	let nodeBefore = syntaxTree.resolveInner(context.pos, -1)

	if (nodeBefore.name === 'TemplateString') {
		return {
			from: word.from,
			options: columnOptions.value,
		}
	}
	if (nodeBefore.name === 'VariableName') {
		return {
			from: word.from,
			options: Object.keys(FUNCTIONS).map((label) => ({ label })),
		}
	}
}

const codeEditor = ref(null)
const helpInfo = ref(null)
const codeViewUpdate = debounce(function ({ cursorPos }) {
	setCompletionPosition()
	helpInfo.value = null
	const tokens = parse(expressionColumn.value.expression.raw).tokens
	const token = tokens
		.filter((t) => t.start <= cursorPos - 1 && t.end >= cursorPos && t.type == 'FUNCTION')
		.at(-1)
	if (token) {
		const { value } = token
		if (FUNCTIONS[value]) {
			helpInfo.value = FUNCTIONS[value]
		}
	}
}, 300)

const helpInfoRefreshKey = ref(0)
const observer = new ResizeObserver(() => {
	helpInfoRefreshKey.value += 1
})
onMounted(() => {
	codeEditor.value && observer.observe(codeEditor.value)
})

const COLUMN_TYPES = [
	{ label: 'String', value: 'String' },
	{ label: 'Integer', value: 'Integer' },
	{ label: 'Decimal', value: 'Decimal' },
	{ label: 'Text', value: 'Text' },
	{ label: 'Datetime', value: 'Datetime' },
	{ label: 'Date', value: 'Date' },
	{ label: 'Time', value: 'Time' },
]

function setCompletionPosition() {
	const completion = document.querySelector('.cm-tooltip-autocomplete')
	if (!completion) return

	const cursor = document.querySelector('.cm-cursor.cm-cursor-primary')
	const left = Number(cursor.style.left.replace('px', ''))
	const top = Number(cursor.style.top.replace('px', ''))

	completion.setAttribute('style', `left: ${left}px !important; top: ${top + 20}px !important;`)
}

const applyDisabled = computed(() => {
	return (
		!expressionColumn.value.label ||
		!expressionColumn.value.type ||
		!expressionColumn.value.expression.raw ||
		!expressionColumn.value.expression.ast
	)
})

function updateColumn() {
	emit('update:column', { ...expressionColumn.value })
	expressionColumn.value = {
		label: '',
		type: 'String',
		expression: {
			raw: '',
			ast: null,
		},
	}
}
</script>

<template>
	<div class="space-y-3 text-base">
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Expression</span>
			<div ref="codeEditor" class="form-input min-h-[7rem] border border-gray-400 p-0">
				<Code
					:modelValue="expressionColumn.expression.raw"
					:completions="getCompletions"
					:autofocus="false"
					placeholder="Write an expression"
					@focus="focused = true"
					@blur="focused = false"
					@viewUpdate="codeViewUpdate"
					@update:modelValue="
						expressionColumn.expression = {
							raw: $event,
							ast: parse($event).ast,
						}
					"
				></Code>
			</div>
		</div>
		<Input
			type="text"
			label="Label"
			class="w-full"
			v-model="expressionColumn.label"
			placeholder="Label"
		/>
		<Input label="Type" type="select" :options="COLUMN_TYPES" v-model="expressionColumn.type" />
	</div>

	<Button
		class="mt-8 w-full"
		variant="solid"
		label="Apply Changes"
		:disabled="applyDisabled"
		@click="updateColumn"
	/>

	<UsePopover
		v-if="codeEditor"
		:show="focused && Boolean(helpInfo)"
		:targetElement="codeEditor"
		placement="left-start"
		:key="helpInfoRefreshKey"
	>
		<div class="-ml-[20rem] flex w-[10rem] flex-col space-y-1.5 text-sm transition-all">
			<div v-show="helpInfo" class="ml-auto w-[20rem] rounded border bg-white p-2 shadow-lg">
				<p>{{ helpInfo?.description }}</p>
				<div class="mt-2 rounded bg-gray-50 p-2 text-xs leading-5">
					<code>
						<span class="text-gray-600"># Syntax</span>
						<br />
						{{ helpInfo?.syntax }}
						<br />
						<br />
						<span class="text-gray-600"># Example</span>
						<br />
						{{ helpInfo?.example }}
					</code>
				</div>
			</div>
		</div>
	</UsePopover>
</template>

<style lang="scss">
.cm-editor {
	user-select: text;
	padding: 0px !important;
	position: relative !important;
}
.cm-gutters {
	display: none !important;
}
.cm-tooltip-autocomplete {
	position: absolute !important;
}
</style>
