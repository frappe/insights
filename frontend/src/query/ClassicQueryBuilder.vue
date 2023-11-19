<template>
	<div v-if="query.doc?.name" class="flex h-full w-full flex-col">
		<div class="flex flex-1 flex-shrink-0 gap-4 overflow-y-scroll">
			<TablePanel />
			<ColumnPanel />
			<FilterPanel />
		</div>
		<div class="flex w-full flex-1 flex-shrink-0 overflow-hidden rounded border py-4">
			<ResultSection>
				<template #footer> <LimitsAndOrder /> </template>
			</ResultSection>
		</div>
	</div>
</template>

<script setup>
import ColumnPanel from '@/query/Column/ColumnPanel.vue'
import FilterPanel from '@/query/Filter/FilterPanel.vue'
import ResultSection from '@/query/ResultSection.vue'
import TablePanel from '@/query/Table/TablePanel.vue'
import { updateDocumentTitle } from '@/utils'
import { computed, inject } from 'vue'
import LimitsAndOrder from './LimitsAndOrder.vue'

const query = inject('query')

const pageMeta = computed(() => ({
	title: query.doc?.title,
	subtitle: query.doc?.name,
}))
updateDocumentTitle(pageMeta)
</script>
