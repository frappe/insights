<script setup>
import Code from '@/components/Controls/Code.vue'
import UsePopover from '@/components/UsePopover.vue'
import { parse } from '@/utils/expressions'
import { FUNCTIONS } from '@/utils/query'
import { debounce } from 'frappe-ui'
import { computed, inject, onMounted, ref } from 'vue'

const query = inject('query')
const emit = defineEmits(['update:modelValue'])
const props = defineProps({ modelValue: Object, placeholder: String })
const expression = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', { raw: value.raw, ast: value.ast }),
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
	helpInfo.value = null
	const tokens = parse(expression.value.raw).tokens
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
	observer.observe(codeEditor.value)
})
</script>

<template>
	<div class="max-w-[20rem] pl-1 pr-2 text-gray-800">
		<div
			ref="codeEditor"
			class="max-h-7 overflow-hidden py-0.5 transition-all"
			:class="focused && '!max-h-[30rem]'"
		>
			<Code
				:value="expression.raw"
				:completions="getCompletions"
				:autofocus="false"
				@focus="focused = true"
				@blur="focused = false"
				@viewUpdate="codeViewUpdate"
				@update:modelValue="
					expression = {
						raw: $event,
						ast: parse($event).ast,
					}
				"
			></Code>
		</div>
	</div>

	<UsePopover
		v-if="codeEditor"
		:show="focused && Boolean(helpInfo)"
		:targetElement="codeEditor"
		placement="bottom-start"
		:key="helpInfoRefreshKey"
	>
		<div class="flex w-[10rem] flex-col space-y-1.5 text-sm transition-all">
			<div
				v-show="helpInfo"
				class="ml-auto w-[20rem] rounded-md border bg-white p-2 shadow-lg"
			>
				<span class="mr-1 font-light">Syntax:</span>
				<span class="font-medium italic" style="font-family: 'Fira Code'">
					{{ helpInfo?.syntax }}
				</span>
				<br />
				<br />
				<span>{{ helpInfo?.description }}</span>
				<br />
				<br />
				<span class="mr-1 font-light">Example:</span>
				<span class="font-medium" style="font-family: 'Fira Code'">
					{{ helpInfo?.example }}
				</span>
			</div>
		</div>
	</UsePopover>
</template>
