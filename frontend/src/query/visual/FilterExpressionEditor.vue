<script setup>
import Code from '@/components/Controls/Code.vue'
import ExpressionHelp from '@/components/ExpressionHelp.vue'
import UsePopover from '@/components/UsePopover.vue'
import { parse } from '@/utils/expressions'
import { FUNCTIONS } from '@/utils/query'
import { debounce } from 'frappe-ui'
import { computed, inject, onMounted, ref } from 'vue'
import { getSelectedTables } from './useAssistedQuery'

const query = inject('query')
const assistedQuery = inject('assistedQuery')
const emit = defineEmits(['update:filter'])
const props = defineProps({ filter: Object })

const filter = computed({
	get: () => props.filter,
	set: (val) =>
		emit('update:filter', {
			expression: {
				raw: val.expression.raw,
				ast: val.expression.ast,
			},
		}),
})

const focused = ref(false)
const columnCompletions = computed(() => {
	// a list of options for code autocompletion
	const selectedTables = getSelectedTables(assistedQuery)
	return assistedQuery.columnOptions
		.filter((c) => selectedTables.includes(c.table))
		.map((c) => ({ label: `${c.table}.${c.column}` }))
})
const getCompletions = (context, syntaxTree) => {
	let word = context.matchBefore(/\w*/)
	let nodeBefore = syntaxTree.resolveInner(context.pos, -1)

	if (nodeBefore.name === 'TemplateString') {
		return {
			from: word.from,
			options: columnCompletions.value,
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
	if (!filter.value.expression?.raw) return
	setCompletionPosition()
	helpInfo.value = null
	const tokens = parse(filter.value.expression.raw).tokens
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

function setCompletionPosition() {
	const completion = document.querySelector('.cm-tooltip-autocomplete')
	if (!completion) return

	const cursor = document.querySelector('.cm-cursor.cm-cursor-primary')
	const left = Number(cursor.style.left.replace('px', ''))
	const top = Number(cursor.style.top.replace('px', ''))

	completion.setAttribute('style', `left: ${left}px !important; top: ${top + 20}px !important;`)
}
</script>

<template>
	<div class="exp-editor space-y-3 text-base">
		<div>
			<span class="mb-2 block text-sm leading-4 text-gray-700">Expression</span>
			<div ref="codeEditor" class="form-input min-h-[7rem] border border-gray-400 p-0">
				<Code
					:modelValue="filter.expression.raw"
					:completions="getCompletions"
					:autofocus="false"
					placeholder="Write an expression"
					@focus="focused = true"
					@blur="focused = false"
					@viewUpdate="codeViewUpdate"
					@update:modelValue="
						filter.expression = {
							raw: $event,
							ast: parse($event).ast,
						}
					"
				></Code>
			</div>
		</div>
	</div>

	<UsePopover
		v-if="codeEditor"
		:show="focused && Boolean(helpInfo)"
		:targetElement="codeEditor"
		placement="right-start"
		:key="helpInfoRefreshKey"
	>
		<div class="w-[10rem] text-sm transition-all">
			<ExpressionHelp v-show="helpInfo?.syntax" :info="helpInfo" />
		</div>
	</UsePopover>
</template>

<style>
.exp-editor .cm-tooltip-autocomplete {
	position: absolute !important;
}
</style>
