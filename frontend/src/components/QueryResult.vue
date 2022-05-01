<template>
	<div class="flex h-full w-full flex-1 select-text rounded-md bg-white text-base">
		<div
			v-if="!result || result.length === 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>Select at least one column to display the result</p>
		</div>

		<div v-else class="flex h-full w-full flex-1 flex-col">
			<!-- Table -->
			<div class="relative flex-1 overflow-scroll rounded-md ring-1 ring-black ring-opacity-5 scrollbar-hide">
				<table class="border-separate">
					<thead class="sticky top-0 bg-white">
						<tr>
							<th
								class="sticky top-0 flex h-10 w-[3rem] items-center justify-center whitespace-nowrap border-b border-r bg-white px-2 text-center font-normal text-gray-500"
								scope="col"
							>
								<!-- <FeatherIcon name="settings" class="h-4 w-4 cursor-pointer" /> -->
							</th>
							<th
								v-for="column in columns"
								:key="column.name"
								class="h-10 whitespace-nowrap border-b px-2 text-left font-normal text-gray-500"
								scope="col"
							>
								<ColumnHeader :column="column" :query="query" />
							</th>
						</tr>
					</thead>
					<tbody class="pointer-events-none bg-white">
						<tr v-for="(row, i) in data" :key="i">
							<td class="sticky left-0 w-[3rem] whitespace-nowrap border-r bg-white p-2 text-center text-gray-500">
								{{ i + 1 }}
							</td>
							<td
								v-for="(cell, j) in row"
								:key="j"
								class="whitespace-nowrap p-2 pr-4 text-gray-500"
								:class="{ 'text-right': number_columns[j] }"
							>
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
	props: ['query'],
	computed: {
		result() {
			return JSON.parse(this.query.doc.result || '[]')
		},
		columns() {
			return this.query.doc.columns || []
		},
		data() {
			return this.result.slice(1)
		},
		number_columns() {
			const number_datatypes = ['int', 'decimal', 'bigint', 'float', 'double']
			return this.columns.map((c) => number_datatypes.includes(c.type.toLowerCase()))
		},
	},
}
</script>
