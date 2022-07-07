<template>
	<BasePage v-if="query.doc">
		<template #header>
			<!-- Height 5 rem -->
			<div class="flex flex-1 items-center justify-between">
				<input
					type="text"
					v-model="query.doc.title"
					ref="titleInput"
					spellcheck="false"
					@blur="query.reload()"
					:size="Math.max(query.doc.title.length, 4)"
					@keydown.enter="updateTitle"
					class="-mx-2 -my-1 rounded border-none bg-transparent p-0 px-2 py-1 text-3xl font-medium caret-black focus:border-none focus:bg-gray-100/75 focus:outline-none focus:ring-transparent"
				/>
				<div class="flex space-x-2">
					<QueryMenu />
				</div>
			</div>
		</template>

		<template #main>
			<div class="flex flex-1 flex-col">
				<TabSwitcher :tabs="tabs" @tab_switched="(tab) => (active_tab = tab)" />
				<!-- 100% - 2.5rem (tabs) -->
				<div class="flex h-[calc(100%-2rem)] min-h-[26rem] w-full rounded-md">
					<QueryBuilder v-show="active_tab == 'Build'" />
					<QueryResult v-show="active_tab == 'Result'" :query="query.resource" />
					<QueryTransform v-show="active_tab == 'Transform'" :query="query.resource" />
					<QueryChart v-if="active_tab == 'Visualize'" :query="query.resource" />
				</div>
			</div>
		</template>
	</BasePage>
</template>

<script setup>
import BasePage from '@/components/BasePage.vue'

import TabSwitcher from '@/components/TabSwitcher.vue'
import QueryBuilder from '@/components/Query/QueryBuilder.vue'
import QueryResult from '@/components/Query/QueryResult.vue'
import QueryTransform from '@/components/Query/QueryTransform.vue'
import QueryChart from '@/components/Query/QueryChart.vue'
import QueryMenu from '@/components/Query/QueryMenu.vue'

import Query from '@/controllers/query'
import { updateDocumentTitle } from '@/utils/document'
import { computed, ref, provide, inject } from 'vue'

const tabs = ref(['Build', 'Result', 'Transform', 'Visualize'])
const active_tab = ref('Build')

const props = defineProps(['name'])
const query = new Query(props.name)
provide('query', query)

const pageMeta = computed(() => {
	return {
		title: query.doc?.name,
		subtitle: 'Query',
	}
})
updateDocumentTitle(pageMeta)

const tableLabels = computed(() => {
	return query.tables.map((table) => table.label).join(', ')
})
const executionTime = computed(() => {
	return Math.round(query.doc.execution_time * 100) / 100
})

const $notify = inject('$notify')
const titleInput = ref(null)
const updateTitle = () => {
	if (!query.doc.title || query.doc.title.length == 0) {
		// TODO: restore old title without fetching the doc again
		// (?) create a local cache of the old document and compare it to the new one
		return query.reload()
	}
	query.setValue('title', query.doc.title).then(() => {
		$notify({
			title: 'Query title updated',
			appearance: 'success',
		})
		titleInput.value.blur()
	})
}
</script>
