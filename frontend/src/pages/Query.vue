<template>
	<BasePage v-if="query.doc">
		<template #header>
			<!-- Height 2.5 rem -->
			<div class="flex flex-1 items-center justify-between">
				<QueryHeader />
				<Tabs :tabs="tabs" @switch="switchTab" />
			</div>
		</template>

		<template #main>
			<div class="flex h-full w-full flex-col rounded-md">
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
const needsExecution = computed(() => query.doc?.status === 'Pending Execution')
const noColumns = computed(() => query.doc?.columns.length === 0)
watchEffect(() => {
	tabs.value.find((t) => t.label === 'Visualize').disabled =
		needsExecution.value || noColumns.value
})
const switchTab = (tab) => {
	if (tab.label === 'Visualize') {
		let warnMessage = ''
		if (needsExecution.value) {
			warnMessage = 'You need to execute the query first.'
		} else if (noColumns.value) {
			warnMessage = 'You need to add columns first.'
		}
		if (warnMessage) {
			$notify({
				title: 'Cannot Visualize',
				message: warnMessage,
				appearance: 'warning',
			})
			return
		}
	}
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
