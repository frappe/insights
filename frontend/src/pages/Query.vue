<template>
	<div v-if="query.doc">
		<header class="flex flex-col">
			<!-- Height 5 rem -->
			<div class="flex h-[5rem] justify-between pt-3">
				<div class="relative flex flex-col items-start space-y-1">
					<input
						type="text"
						v-model="query.doc.title"
						ref="titleInput"
						spellcheck="false"
						@blur="query.reload()"
						:size="Math.max(query.doc.title.length, 4)"
						@keydown.enter="updateTitle"
						class="-mx-2 -my-1 rounded border-none bg-transparent p-0 px-2 py-1 text-3xl font-bold caret-black focus:border-none focus:bg-gray-100/75 focus:outline-none focus:ring-transparent"
					/>
					<div class="flex space-x-3 text-base font-light text-gray-600">
						<div v-if="query.dataSource" class="flex items-center">
							<FeatherIcon name="database" class="mr-1.5 h-3 w-3" />
							<span> {{ query.dataSource }} </span>
						</div>
						<div v-if="tableLabels" class="flex items-center">
							<FeatherIcon name="layout" class="mr-1.5 h-3 w-3" />
							<span> {{ tableLabels }} </span>
						</div>
						<div v-if="executionTime" class="flex items-center">
							<FeatherIcon name="clock" class="mr-1.5 h-3 w-3" />
							<span> Took {{ executionTime }} sec </span>
						</div>
					</div>
				</div>
				<div class="flex space-x-2">
					<QueryMenu />
				</div>
			</div>
			<!-- Height 2.5rem -->
			<TabSwitcher :tabs="tabs" @tab_switched="(tab) => (active_tab = tab)" />
		</header>
		<!-- 100% - 7.5rem (header) + 1rem (margin-top) -->
		<main class="mt-4 flex h-[calc(100%-8.5rem)] min-h-[26rem] w-full rounded-md border bg-white shadow">
			<QueryBuilder v-show="active_tab == 'Build'" />
			<QueryResult v-show="active_tab == 'Result'" :query="query.resource" />
			<QueryTransform v-show="active_tab == 'Transform'" :query="query.resource" />
			<QueryChart v-if="active_tab == 'Visualize'" :query="query.resource" />
		</main>
	</div>
</template>

<script setup>
import TabSwitcher from '@/components/TabSwitcher.vue'
import QueryBuilder from '@/components/Query/QueryBuilder.vue'
import QueryResult from '@/components/Query/QueryResult.vue'
import QueryTransform from '@/components/Query/QueryTransform.vue'
import QueryChart from '@/components/Query/QueryChart.vue'
import QueryMenu from '@/components/Query/QueryMenu.vue'

import moment from 'moment'
import Query from '@/controllers/query'
import { computed, ref, provide, inject } from 'vue'

const tabs = ref(['Build', 'Result', 'Transform', 'Visualize'])
const active_tab = ref('Build')

const props = defineProps(['name'])
const query = new Query(props.name)
provide('query', query)

const tableLabels = computed(() => {
	return query.tables.map((table) => table.label).join(', ')
})
const lastUpdated = computed(() => {
	return moment(query.doc.modified).fromNow()
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
