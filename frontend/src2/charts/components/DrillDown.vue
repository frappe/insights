<script setup lang="ts">
import { debounce } from 'frappe-ui'
import { Combine } from 'lucide-vue-next'
import { inject, provide, ref, nextTick } from 'vue'
import { wheneverChanges } from '../../helpers'
import QueryExecutionStatus from '../../query/components/QueryExecutionStatus.vue'
import QueryToolbar from '../../query/components/QueryToolbar.vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import QueryOperations from '../../query/components/QueryOperations.vue'
import { count, makeDimension } from '../../query/helpers'
import { Query } from '../../query/query'
import { QueryResultColumn } from '../../types/query.types'
import { Dashboard } from '../../dashboard/dashboard'
import { __ } from '../../translation'

const props = defineProps<{ query: Query }>()

const dashboard = inject<Dashboard>('dashboard')!
const chartName = inject<string>('chartName', '')
if (dashboard && chartName) {
	const adhocFilters = dashboard.getAdhocFilters(chartName)
	if (adhocFilters) {
		props.query.adhocFilters = adhocFilters
	}
}

const show = defineModel<boolean>()
const isQueryReady = ref(false)

wheneverChanges(
	show,
	() => {
		if (show.value) {
			isQueryReady.value = false
			nextTick(async () => {
				await props.query.execute(true)
				isQueryReady.value = true
			})
		}
	},
	{ immediate: true },
)

provide('query', props.query)

const drillDownQuery = ref<Query>()
const showDrillDown = ref(false)
function openDrillDown(query: Query) {
	drillDownQuery.value = query
	showDrillDown.value = true
}

function _groupBy(column: QueryResultColumn) {
	props.query.addSummarize({
		dimensions: [makeDimension(column)],
		measures: [count()],
	})
}
// FIX: debug why groupBy is called twice
const groupBy = debounce(_groupBy, 50)
</script>

<template>
	<Dialog v-model:open="show" :title="__('Drill Down')" size="5xl">
		<template #default>
			<div v-if="!isQueryReady" class="flex h-[32rem] w-full items-center justify-center">
				<LoadingIndicator class="h-5 w-5 text-ink-gray-5" />
			</div>
			<div v-else class="relative flex h-[32rem] w-full flex-1 gap-4 overflow-hidden">
				<div class="flex h-full flex-1 flex-col gap-2 overflow-hidden p-0.5">
					<QueryToolbar>
						<QueryExecutionStatus />
					</QueryToolbar>
					<div class="flex flex-1 overflow-hidden rounded border border-outline-gray-2">
						<QueryDataTable
							:enable-sort="true"
							:enable-drill-down="true"
							@drill-down="openDrillDown"
							:query="props.query"
						>
							<template #header-prefix="{ column }">
								<Tooltip text="Group By" :hover-delay="0.2">
									<Button
										variant="ghost"
										class="rounded-none"
										@click="() => groupBy(column)"
									>
										<template #icon>
											<Combine
												class="h-4 w-4 text-ink-gray-6"
												stroke-width="1.5"
											/>
										</template>
									</Button>
								</Tooltip>
							</template>
						</QueryDataTable>
					</div>
				</div>
				<div
					class="relative flex h-full w-[17rem] flex-shrink-0 overflow-y-auto rounded border border-outline-gray-2"
				>
					<QueryOperations />
				</div>
			</div>
		</template>
	</Dialog>

	<DrillDown
		v-if="drillDownQuery"
		v-model="showDrillDown"
		@update:modelValue="!$event ? (drillDownQuery = undefined) : undefined"
		:query="drillDownQuery"
	>
	</DrillDown>
</template>
