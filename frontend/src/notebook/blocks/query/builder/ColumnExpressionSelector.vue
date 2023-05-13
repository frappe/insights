<script setup>
import Code from '@/components/Controls/Code.vue'
import { parse } from '@/utils/expressions'
import { FUNCTIONS } from '@/utils/query'
import { computed, inject, ref } from 'vue'

const query = inject('query')
const emit = defineEmits(['update:modelValue'])
const props = defineProps({ modelValue: Object, placeholder: String })
const expression = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
})

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
</script>

<template>
	<div class="flex max-w-[20rem] rounded-lg border border-gray-300 px-1 py-0.5 text-gray-800">
		<Code
			:value="expression.raw"
			:completions="getCompletions"
			@update:modelValue="
				expression = {
					raw: $event,
					ast: parse($event).ast,
				}
			"
		></Code>
	</div>
</template>
