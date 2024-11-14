<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { LoadingIndicator } from 'frappe-ui'
import { Play, RefreshCw } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import Code from '../../components/Code.vue'
import DataTable from '../../components/DataTable.vue'
import { Query } from '../query'

const query = inject<Query>('query')!

const sql = ref<string>(query.getSQLQuery())
function execute() {
	query.setSQLQuery(sql.value, 'demo_data')
}

const columns = computed(() => query.result.columns)
const rows = computed(() => query.result.formattedRows)
const previewRowCount = computed(() => query.result.rows.length.toLocaleString())
const totalRowCount = computed(() =>
	query.result.totalRowCount ? query.result.totalRowCount.toLocaleString() : ''
)
</script>

<template>
	<div class="flex flex-1 flex-col gap-4 overflow-hidden p-4">
		<div class="relative flex h-[55%] w-full flex-col rounded border">
			<div class="flex-1">
				<Code v-model="sql" />
			</div>

			<div class="absolute bottom-2 left-10">
				<Button class="h-8 w-8 bg-white shadow" variant="ghost" @click="execute">
					<template #icon>
						<Play class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</div>
		</div>
		<div
			v-show="query.result.executedSQL"
			class="tnum flex flex-shrink-0 items-center gap-2 text-sm text-gray-600"
		>
			<div class="h-2 w-2 rounded-full bg-green-500"></div>
			<div>
				<span v-if="query.result.timeTaken == -1"> Fetched from cache </span>
				<span v-else> Fetched in {{ query.result.timeTaken }}s </span>
				<span> {{ useTimeAgo(query.result.lastExecutedAt).value }} </span>
			</div>
		</div>
		<div class="relative flex w-full flex-1 flex-col overflow-hidden rounded border">
			<div
				v-if="query.executing"
				class="absolute top-10 z-10 flex w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
			>
				<LoadingIndicator class="h-8 w-8 text-gray-700" />
			</div>

			<DataTable :columns="columns" :rows="rows" :on-export="query.downloadResults">
				<template #footer-left>
					<div class="tnum flex items-center gap-2 text-sm text-gray-600">
						<span> Showing {{ previewRowCount }} of </span>
						<span v-if="!totalRowCount" class="inline-block">
							<Tooltip text="Load Count">
								<RefreshCw
									v-if="!query.fetchingCount"
									class="h-3.5 w-3.5 cursor-pointer transition-all hover:text-gray-800"
									stroke-width="1.5"
									@click="query.fetchResultCount"
								/>
								<LoadingIndicator v-else class="h-3.5 w-3.5 text-gray-600" />
							</Tooltip>
						</span>
						<span v-else> {{ totalRowCount }} </span>
						rows
					</div>
				</template>
			</DataTable>
		</div>
	</div>
</template>
