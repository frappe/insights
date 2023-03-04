<template>
	<div v-if="query.doc" class="flex h-full w-full flex-col overflow-scroll scrollbar-hide">
		<div class="flex flex-shrink-0 items-center justify-between py-1 px-2">
			<QueryHeader />
			<Tabs v-if="!hideTabs" class="w-40" :tabs="tabs" @switch="switchTab" />
		</div>

		<template v-if="activeTab == 'Build'">
			<div class="flex flex-1 flex-shrink-0 gap-2">
				<TablePanel />
				<ColumnPanel />
				<FilterPanel />
			</div>
			<QueryResult />
		</template>

		<template v-if="activeTab == 'Visualize'">
			<QueryVisualizer />
		</template>
	</div>
</template>

<script setup>
import Tabs from '@/components/Tabs.vue'
import ColumnPanel from '@/query/Column/ColumnPanel.vue'
import FilterPanel from '@/query/Filter/FilterPanel.vue'
import QueryHeader from '@/query/QueryHeader.vue'
import QueryVisualizer from '@/query/QueryVisualizer.vue'
import QueryResult from '@/query/Result/QueryResult.vue'
import TablePanel from '@/query/Table/TablePanel.vue'
import { useQuery } from '@/utils/query'
import { computed, inject, provide, ref } from 'vue'

const props = defineProps(['name', 'hideTabs'])
const query = props.name ? useQuery(props.name) : inject('queryBuilder').currentQuery
provide('query', query)

const tabs = ref([
	{ label: 'Build', active: true },
	{ label: 'Visualize', active: false },
])
const activeTab = computed(() => tabs.value.find((t) => t.active).label)
const switchTab = (tab) => {
	tabs.value.forEach((t) => {
		t.active = t.label === tab.label
	})
}
</script>
