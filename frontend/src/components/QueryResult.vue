<template>
	<div class="flex h-full w-full flex-1 select-text rounded-md bg-white text-base">
		<div
			v-if="!result || result.length === 0"
			class="m-4 flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>Select at least one column to display the result</p>
		</div>

		<div v-else class="flex h-full w-full flex-1 flex-col">
			<!-- Table -->
			<div class="flex-1 overflow-scroll ring-1 ring-black ring-opacity-5 scrollbar-hide">
				<table class="min-w-full divide-y divide-gray-300">
					<thead class="sticky top-0 h-10 bg-gray-50">
						<tr class="divide-x divide-gray-200">
							<th
								class="sticky top-0 w-[3rem] whitespace-nowrap bg-gray-50 px-2 py-1 text-center font-normal text-gray-500"
								scope="col"
							></th>
							<th
								v-for="column in columns"
								:key="column.name"
								class="whitespace-nowrap px-2 py-1 text-left font-normal text-gray-500"
								scope="col"
							>
								<ColumnHeader :column="column" :query="query" />
							</th>
						</tr>
					</thead>
					<tbody class="pointer-events-none divide-y divide-gray-200 bg-white">
						<tr v-for="(row, i) in data" :key="i" class="divide-x divide-gray-200">
							<td class="sticky left-0 w-[3rem] whitespace-nowrap bg-gray-50 px-2 py-2 text-center text-gray-500">
								{{ i + 1 }}
							</td>
							<td v-for="(cell, j) in row" :key="j" class="whitespace-nowrap px-2 py-2 text-gray-500">
								{{ cell }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>
		</div>
	</div>
</template>

<script>
import ColumnHeader from './ColumnHeader.vue'

export default {
	name: 'QueryResult',
	components: {
		ColumnHeader,
	},
	props: ['result', 'query'],
	computed: {
		columns() {
			return this.query.doc.columns || []
		},
		data() {
			return this.result.slice(1)
		},
	},
}
</script>
