<template>
	<BasePage v-if="query.doc">
		<template #header>
			<!-- Height 5 rem -->
			<div class="flex flex-1 items-start justify-between">
				<input
					type="text"
					v-model="query.doc.title"
					ref="titleInput"
					spellcheck="false"
					@blur="query.reload.submit()"
					@keydown.enter="updateTitle"
					class="-mx-2 flex-1 rounded border-none bg-transparent p-0 py-1 px-2 text-3xl font-medium caret-black focus:border-none focus:bg-gray-100/75 focus:outline-none focus:ring-transparent"
				/>
				<div class="ml-4">
					<QueryMenu />
				</div>
			</div>
		</template>

		<template #main>
			<div class="flex h-full w-full flex-col">
				<div class="-mt-1 mb-3 flex h-5 space-x-3 text-sm font-light text-gray-600">
					<div v-if="query.doc.data_source" class="flex items-center">
						<FeatherIcon name="database" class="mr-1.5 h-3 w-3" />
						<span> {{ query.doc.data_source }} </span>
					</div>
					<div v-if="tableLabels" class="flex items-center">
						<FeatherIcon name="layout" class="mr-1.5 h-3 w-3" />
						<span> {{ tableLabels }} </span>
					</div>
					<div v-if="executionTime" class="flex items-center">
						<FeatherIcon name="clock" class="mr-1.5 h-3 w-3" />
						<span> {{ executionTime }} sec </span>
					</div>
				</div>
				<TabSwitcher :tabs="tabs" :activeTab="activeTab" @tab-switched="onTabSwitch" />
				<!-- 100% - (h-5 + mb-3 - -mt-1 = 1.75rem) - (2rem) -->
				<div class="flex h-[calc(100%-3.25rem)] w-full rounded-md">
					<QueryBuilder v-show="activeTab == 'Build'" />
					<QueryResult v-if="activeTab == 'Result'" />
					<QueryVisualizer v-if="activeTab == 'Visualize'" />
				</div>
			</div>
		</template>
	</BasePage>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'

import TabSwitcher from '@/components/TabSwitcher.vue'
import QueryMenu from '@/components/Query/QueryMenu.vue'
import QueryBuilder from '@/components/Query/QueryBuilder.vue'
import QueryResult from '@/components/Query/Result/QueryResult.vue'
import QueryVisualizer from '@/components/Query/Visualization/QueryVisualizer.vue'

import { useQuery } from '@/utils/query'
import { updateDocumentTitle } from '@/utils'
import { computed, ref, provide, inject, watchEffect } from 'vue'

const props = defineProps(['name'])
const $notify = inject('$notify')
const query = useQuery(props.name)
provide('query', query)

const tabs = ref([
	{
		label: 'Build',
		showIndicator: false,
		disabled: false,
		disabledMessage: '',
	},
	{
		label: 'Result',
		showIndicator: false,
		disabled: false,
		disabledMessage: '',
	},
	{
		label: 'Visualize',
		showIndicator: false,
		disabled: false,
		disabledMessage: '',
	},
])
const activeTab = ref('Build')
const needsExecution = computed(() => query.doc?.status === 'Pending Execution')
watchEffect(() => {
	tabs.value.find((t) => t.label === 'Visualize').disabled = needsExecution.value
	tabs.value.find((tab) => tab.label === 'Result').showIndicator = needsExecution.value
})
const onTabSwitch = (tab) => {
	if (tab.label === 'Visualize' && needsExecution.value) {
		$notify({
			title: 'You need to execute the query first',
			appearance: 'warning',
		})
		return
	}
	activeTab.value = tab.label
}

const tableLabels = computed(() => {
	return query.tables.data?.map((table) => table.label).join(', ')
})
const executionTime = computed(() => {
	return Math.round(query.doc.execution_time * 100) / 100
})

const titleInput = ref(null)
const updateTitle = () => {
	if (!query.doc.title || query.doc.title.length == 0) {
		// TODO: restore old title without fetching the doc again
		// (?) create a local cache of the old document and compare it to the new one
		return query.reload.submit()
	}
	query.setValue.submit({ title: query.doc.title }).then(() => {
		$notify({
			title: 'Query title updated',
			appearance: 'success',
		})
		titleInput.value.blur()
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
