<template>
	<div class="flex items-center justify-between rounded-b-md px-1 text-base">
		<!-- <div v-if="orderByColumns.length" class="flex items-center space-x-1">
			<span class="text-gray-600">Sorted by</span>
			<div class="flex items-center space-x-1">
				<span
					v-for="(column, index) in orderByColumns"
					:key="index"
					class="flex items-center space-x-1 font-medium"
				>
					<span>{{ column.label }}</span>
					<span class="text-gray-600">{{ getOrder(column.label) }}</span>
					<span v-if="index < orderByColumns.length - 1" class="text-gray-600">,</span>
				</span>
			</div>
		</div> -->
		<div v-if="queriedRowCount >= 0" class="flex items-center space-x-1">
			<span class="text-gray-600">Showing</span>
			<span class="font-mono"> {{ displayedRowCount }}</span>
			<span class="text-gray-600">out of</span>
			<span class="font-mono">{{ queriedRowCount }}</span>
			<span class="text-gray-600">rows in</span>
			<span class="font-mono">{{ executionTime }}</span>
			<span class="text-gray-600">seconds</span>
		</div>
		<div class="ml-auto flex items-center space-x-1">
			<span class="text-gray-600">Limit to</span>
			<input
				type="text"
				ref="limitInput"
				v-model.number="limit"
				:size="String(limit).length"
				class="form-input"
				@keydown.enter.stop="$refs.limitInput.blur()"
				@keydown.esc.stop="$refs.limitInput.blur()"
			/>
			<span class="text-gray-600">rows</span>
		</div>
	</div>
</template>

<script setup>
import { computed, inject, ref } from 'vue'

const query = inject('query')
const executionTime = computed(() => query.doc.execution_time)
const queriedRowCount = computed(() => query.doc.results_row_count)
const displayedRowCount = computed(() => Math.min(query.MAX_ROWS, queriedRowCount.value))

const assistedQuery = inject('assistedQuery')
const limitInput = ref(null)
const limit = computed({
	get: () => assistedQuery.limit,
	set: (value) => (assistedQuery.limit = value || 100),
})
const orderByColumns = computed(() => {
	return assistedQuery.columns.filter((c) => c.order)
})
function getOrder(columnLabel) {
	return assistedQuery.columns.find((c) => c.label == columnLabel)?.order
}
</script>
