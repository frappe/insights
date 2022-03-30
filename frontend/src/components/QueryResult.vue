<template>
	<div class="flex h-full flex-1 rounded-md bg-white p-4 text-base shadow">
		<div
			v-if="!result || result.length === 0"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>Select atleast one table & column to display the result</p>
		</div>
		<div
			v-else
			class="h-full overflow-y-scroll rounded-md shadow ring-1 ring-black ring-opacity-5"
		>
			<table class="min-w-full divide-y divide-gray-300">
				<thead class="sticky top-0 bg-gray-50">
					<tr class="divide-x divide-gray-200">
						<th
							class="whitespace-nowrap px-2 py-1 text-left font-normal text-gray-500"
							scope="col"
						>
							#
						</th>
						<th
							v-for="(column, idx) in columns"
							:key="idx"
							class="whitespace-nowrap px-2 py-1 text-left font-normal text-gray-500"
							scope="col"
						>
							{{ column }}
						</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-200 bg-white">
					<tr
						v-for="(row, i) in data"
						:key="i"
						class="divide-x divide-gray-200"
					>
						<td class="whitespace-nowrap px-2 py-2 text-gray-500">
							{{ i + 1 }}
						</td>
						<td
							v-for="(cell, j) in row"
							:key="j"
							class="whitespace-nowrap px-2 py-2 text-gray-500"
						>
							{{ cell }}
						</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</template>

<script>
export default {
	name: 'QueryResult',
	props: ['result'],
	computed: {
		columns() {
			return this.result[0]
		},
		data() {
			return this.result.slice(1)
		},
	},
}
</script>
