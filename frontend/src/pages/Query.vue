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
				class="main flex flex-1 flex-col overflow-scroll rounded-md scrollbar-hide xl:overflow-hidden"
			>
				<QueryBuilder v-if="activeTab == 'Build'" />
				<QueryVisualizer v-if="activeTab == 'Visualize'" />
			</div>
		</template>
	</BasePage>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'

import Tabs from '@/components/Tabs.vue'

import QueryHeader from '@/components/Query/QueryHeader.vue'
import QueryBuilder from '@/components/Query/QueryBuilder.vue'
import QueryVisualizer from '@/components/Query/Visualize/QueryVisualizer.vue'

import { useQuery } from '@/utils/query'
import { updateDocumentTitle } from '@/utils'
import { computed, ref, provide, inject, watchEffect } from 'vue'

const props = defineProps(['name'])
const $notify = inject('$notify')
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
