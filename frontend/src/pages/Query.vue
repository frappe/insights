<template>
	<BasePage v-if="query.doc">
		<template #header>
			<!-- Height 2.5 rem -->
			<div class="flex flex-1 items-center justify-between">
				<QueryHeader />
				<Tabs class="w-40" :tabs="tabs" @switch="switchTab" />
			</div>
		</template>

		<template #main>
			<div
				class="main flex flex-1 flex-col overflow-scroll rounded-md scrollbar-hide lg:overflow-hidden"
			>
				<QueryBuilder v-if="activeTab == 'Build'" />
				<QueryVisualizer v-if="activeTab == 'Visualize'" />
			</div>
		</template>
	</BasePage>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'
import QueryBuilder from '@/components/Query/QueryBuilder.vue'
import QueryHeader from '@/components/Query/QueryHeader.vue'
import QueryVisualizer from '@/components/Query/QueryVisualizer.vue'
import Tabs from '@/components/Tabs.vue'
import { updateDocumentTitle } from '@/utils'
import { useQuery } from '@/utils/query'
import { computed, provide, ref } from 'vue'

const props = defineProps(['name'])
const query = useQuery(props.name)
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

const pageMeta = computed(() => {
	return {
		title: props.name,
		subtitle: 'Query',
	}
})
updateDocumentTitle(pageMeta)
</script>
