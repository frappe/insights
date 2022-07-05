<template>
	<div class="relative flex h-full w-full select-text px-1 pt-4 text-base">
		<div
			v-if="query.columns?.length === 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 font-light text-gray-400"
		>
			<p>Select at least one column to display the result</p>
		</div>

		<div
			v-else-if="!needsExecution && result?.length === 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 font-light text-gray-400"
		>
			<p>No results found</p>
		</div>

		<div
			v-else
			class="relative flex h-full w-full flex-col-reverse"
			:class="{ 'blur-[2px]': needsExecution }"
		>
			<div class="-mb-1 flex h-10 w-full flex-shrink-0 pt-2">
				<LimitsAndOrder />
			</div>
			<!-- Table -->
			<div class="relative h-[calc(100%-2.5rem)] w-full overflow-scroll rounded-md border">
				<table class="border-separate">
					<thead class="sticky top-0 text-gray-600">
						<tr>
							<th
								class="sticky top-0 flex h-10 w-[2.5rem] items-center justify-center whitespace-nowrap border-b border-r bg-white px-2 text-center font-medium"
								scope="col"
							></th>
							<th
								v-for="column in query.columns"
								:key="column.name"
								class="h-10 whitespace-nowrap border-b bg-white px-2 text-left font-medium"
								scope="col"
							>
								<ColumnHeader :column="column" :query="query" />
							</th>
						</tr>
					</thead>
					<tbody class="pointer-events-none">
						<tr v-for="(row, i) in result" :key="i">
							<td
								class="sticky left-0 w-[2.5rem] whitespace-nowrap border-r bg-white text-center font-medium text-gray-600"
							>
								{{ i + 1 }}
							</td>
							<td
								v-for="(cell, j) in row"
								:key="j"
								class="whitespace-nowrap bg-white p-2.5 pr-4 font-light text-gray-600"
								:class="{ 'text-right': isNumberColumn[j] }"
							>
								{{ cell }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>
		<div
			v-if="needsExecution && query.columns?.length > 0"
			class="absolute top-0 left-0 flex h-full w-full items-center justify-center"
		>
			<Button
				appearance="primary"
				class="!shadow-md"
				@click="query.run()"
				:loading="query.resource.run.loading"
			>
				Execute
			</Button>
		</div>
	</div>
</template>

<script setup>
import ColumnHeader from '@/components/Query/ColumnHeader.vue'
import LimitsAndOrder from '@/components/Query/LimitsAndOrder.vue'

import { computed, inject } from 'vue'

const query = inject('query')

const result = computed(() => query.result?.slice(0, 1000))
const needsExecution = computed(() => query.status === 'Pending Execution')
const isNumberColumn = computed(() => {
	return query.doc.columns.map((c) =>
		['Int', 'Decimal', 'Bigint', 'Float', 'Double'].includes(c.type)
	)
})
</script>
