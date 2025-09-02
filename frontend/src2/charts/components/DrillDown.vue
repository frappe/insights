<script setup lang="ts">
import { debounce } from 'frappe-ui'
import { Combine } from 'lucide-vue-next'
import { inject, provide } from 'vue'
import { wheneverChanges } from '../../helpers'
import QueryBuilderToolbar from '../../query/components/QueryBuilderToolbar.vue'
import QueryDataTable from '../../query/components/QueryDataTable.vue'
import QueryOperations from '../../query/components/QueryOperations.vue'
import { count, makeDimension } from '../../query/helpers'
import { Query } from '../../query/query'
import { QueryResultColumn } from '../../types/query.types'
import { Dashboard } from '../../dashboard/dashboard'

const props = defineProps<{ query: Query }>()

const dashboard = inject<Dashboard>('dashboard')!
const chartName = inject<string>('chartName', '')
if (dashboard && chartName) {
	const _adhocFilters = dashboard.getAdhocFilters(chartName)
	if (_adhocFilters) {
		props.query.adhocFilters = _adhocFilters
		// FIX: the query is executed twice; when operations are added and when adhoc filters are set
		props.query.execute()
	}
}

const show = defineModel()
wheneverChanges(
	show,
	() => {
		if (show.value && !props.query.result.executedSQL && !props.query.executing) {
			props.query.execute()
		}
	},
	{ immediate: true },
)

provide('query', props.query)

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
	<Dialog
		v-model="show"
		:options="{
			title: 'Drill Down',
			size: '5xl',
		}"
	>
		<template #body-content>
			<div class="relative flex h-[32rem] w-full flex-1 gap-4 overflow-hidden bg-white">
				<div class="flex h-full flex-1 flex-col gap-2 overflow-hidden p-0.5">
					<QueryBuilderToolbar></QueryBuilderToolbar>
					<div class="flex flex-1 overflow-hidden rounded border">
						<QueryDataTable
							:enable-sort="true"
							:enable-drill-down="true"
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
												class="h-4 w-4 text-gray-700"
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
					class="relative z-[1] flex h-full w-[17rem] flex-shrink-0 overflow-y-auto rounded border bg-white"
				>
					<QueryOperations />
				</div>
			</div>
		</template>
	</Dialog>
</template>
