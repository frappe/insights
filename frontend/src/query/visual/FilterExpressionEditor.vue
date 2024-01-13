<script setup>
import { parse } from '@/utils/expressions'
import { computed, defineProps, inject, reactive } from 'vue'
import ExpressionBuilder from './ExpressionBuilder.vue'
import { NEW_FILTER } from './constants'
import { getSelectedTables } from './useAssistedQuery'

const emptyExpressionFilter = {
	...NEW_FILTER,
	expression: {
		raw: '',
		ast: {},
	},
}

const assistedQuery = inject('assistedQuery')
const props = defineProps({ filter: Object })

const propsFilter = props.filter || emptyExpressionFilter
const filter = reactive({
	...NEW_FILTER,
	...propsFilter,
})
if (!filter.expression) {
	filter.expression = { ...emptyExpressionFilter.expression }
}

const isValid = computed(() => {
	return filter.expression.raw.trim().length > 0 && filter.expression.ast
})

const columnOptions = computed(() => {
	const selectedTables = getSelectedTables(assistedQuery)
	return assistedQuery.columnOptions.filter((c) => selectedTables.includes(c.table)) || []
})

function onSave() {
	if (!isValid.value) return
	emit('save', {
		...filter,
		expression: {
			raw: filter.expression.raw,
			ast: parse(filter.expression.raw).ast,
		},
	})
}
</script>

<template>
	<div class="space-y-3 text-base">
		<div class="flex flex-col justify-between gap-2 lg:flex-row">
			<Button variant="outline" @click="emit('discard')"> Discard </Button>
			<div class="flex flex-col gap-2 lg:flex-row">
				<Button variant="outline" theme="red" @click="emit('remove')">Remove</Button>
				<Button variant="solid" :disabled="!isValid" @click="onSave"> Save </Button>
			</div>
		</div>
	</div>
</template>
