<script setup lang="ts">
import { call } from 'frappe-ui'
import { ref } from 'vue'
import Code from '../../components/Code.vue'
import { ColumnOption } from '../../types/query.types'

const props = defineProps<{ columnOptions: ColumnOption[] }>()
const expression = defineModel<string>({
	required: true,
})

const functionList = ref<string[]>([])
call('insights.insights.doctype.insights_data_source_v3.ibis_functions.get_function_list').then(
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
</script>

<template>
	<div ref="codeContainer" class="flex h-[14rem] w-full overflow-scroll rounded border text-base">
		<Code
			ref="codeEditor"
			language="python"
			class="column-expression"
			v-model="expression"
			:completions="getCompletions"
		></Code>
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
