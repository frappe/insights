<template>
	<div class="flex h-full w-full flex-1 select-text text-base">
		<div
			v-if="!columns || columns.length === 0"
			class="m-4 flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 font-light text-gray-400"
		>
			<p>Select at least one column to display the result</p>
		</div>

		<div
			v-else-if="!result || result.length === 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 font-light text-gray-400"
		>
			<p>No results found</p>
		</div>

		<div v-else class="relative flex h-full w-full flex-1 flex-col">
			<!-- Table -->
			<div
				class="relative h-[100%-2.5rem] w-full overflow-scroll rounded-md"
				:class="{ 'blur-[2px]': needs_execution }"
			>
				<table class="border-separate">
					<thead class="sticky top-0 text-gray-600">
						<tr>
							<th
								class="sticky top-0 flex h-10 w-[2.5rem] items-center justify-center whitespace-nowrap border-b border-r bg-white px-2 text-center font-medium"
								scope="col"
							>
								<!-- <FeatherIcon name="settings" class="h-4 w-4 cursor-pointer" /> -->
							</th>
							<th
								v-for="column in columns"
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
								:class="{ 'text-right': number_columns[j] }"
							>
								{{ cell }}
							</td>
						</tr>
					</tbody>
				</table>
			</div>
			<div class="flex h-10 w-full flex-shrink-0 border-t">
				<LimitsAndOrder :query="query" />
			</div>
			<div v-if="needs_execution" class="absolute top-0 left-0 flex h-full w-full items-center justify-center">
				<Button appearance="primary" class="!shadow-md" @click="query.run.submit()" :loading="query.run.loading">
					Execute
				</Button>
			</div>
		</div>
	</div>
</template>

<script>
import ColumnHeader from '@/components/Query/ColumnHeader.vue'
import LimitsAndOrder from '@/components/Query/LimitsAndOrder.vue'

export default {
	name: 'QueryResult',
	components: {
		ColumnHeader,
		LimitsAndOrder,
	},
	props: ['query'],
	computed: {
		columns() {
			return this.query.doc.columns || []
		},
		result() {
			// show only 10000 rows at most
			const result = JSON.parse(this.query.doc.result || '[]')
			return result.slice(0, 1000)
		},
		number_columns() {
			const number_datatypes = ['int', 'decimal', 'bigint', 'float', 'double']
			return this.columns.map((c) => number_datatypes.includes(c.type.toLowerCase()))
		},
		needs_execution() {
			return this.query.doc.status === 'Pending Execution'
		},
	},
}
</script>
