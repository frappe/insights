<template>
	<div v-if="query.doc?.name" class="flex h-full w-full flex-col pt-4">
		<div class="flex flex-1 flex-shrink-0 gap-4 overflow-y-scroll">
			<TablePanel />
			<ColumnPanel />
			<FilterPanel />
		</div>
		<div class="flex w-full flex-1 flex-shrink-0 overflow-hidden rounded py-4">
			<ResultSection>
				<template #footer> <LimitsAndOrder /> </template>
			</ResultSection>
		</div>
	</div>
</template>

<script setup>
import ResultSection from '@/query/ResultSection.vue'
import { updateDocumentTitle } from '@/utils'
import { computed, inject } from 'vue'
import ColumnPanel from './Column/ColumnPanel.vue'
import FilterPanel from './Filter/FilterPanel.vue'
import LimitsAndOrder from './LimitsAndOrder.vue'
import TablePanel from './Table/TablePanel.vue'

const query = inject('query')

const pageMeta = computed(() => ({
	title: query.doc?.title,
	subtitle: query.doc?.name,
}))
updateDocumentTitle(pageMeta)
</script>
