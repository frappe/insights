<template>
	<div class="flex items-center justify-between rounded-b-md px-1 text-base">
		<div v-if="queriedRowCount >= 0" class="flex items-center space-x-1">
			<span class="text-gray-600">Showing</span>
			<span class="tnum"> {{ displayedRowCount }}</span>
			<span class="text-gray-600">out of</span>
			<span class="tnum">{{ queriedRowCount }}</span>
			<span class="text-gray-600">rows in</span>
			<span class="tnum">{{ executionTime }}</span>
			<span class="text-gray-600">seconds</span>
		</div>
		<div class="ml-auto flex items-center gap-1">
			<Button variant="ghost" icon="download" @click="query.downloadResults"> </Button>
		</div>
	</div>
</template>

<script setup>
import { Download } from 'lucide-vue-next'
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
