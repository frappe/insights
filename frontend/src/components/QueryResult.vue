<template>
	<div class="flex flex-1 bg-white p-4 shadow">
		<div v-if="data" class="flex flex-col">
			<div class="-my-2 -mx-4 overflow-x-auto sm:-mx-6 lg:-mx-8">
				<div class="inline-block min-w-full py-3 align-middle md:px-6 lg:px-8">
					<div
						class="overflow-hidden shadow ring-1 ring-black ring-opacity-5 md:rounded"
					>
						<table class="min-w-full divide-y divide-gray-300">
							<thead class="bg-gray-50">
								<tr class="divide-x divide-gray-200">
									<th
										class="whitespace-nowrap px-2 py-1 text-left text-sm font-normal text-slate-500"
										scope="col"
									>
										#
									</th>
									<th
										v-for="(column, idx) in columns"
										:key="idx"
										class="whitespace-nowrap px-2 py-1 text-left text-sm font-normal text-slate-500"
										scope="col"
									>
										{{ column }}
									</th>
								</tr>
							</thead>
							<tbody class="divide-y divide-gray-200 bg-white">
								<tr
									v-for="(row, i) in rows"
									:key="i"
									class="divide-x divide-gray-200"
								>
									<td class="whitespace-nowrap px-2 py-2 text-sm text-gray-500">
										{{ i + 1 }}
									</td>
									<td
										v-for="(cell, j) in row"
										:key="j"
										class="whitespace-nowrap px-2 py-2 text-sm text-gray-500"
									>
										{{ cell }}
									</td>
								</tr>
							</tbody>
						</table>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'QueryResult',
	props: ['data'],
	computed: {
		columns() {
			return this.data && this.data[0] ? Object.keys(this.data[0]) : []
		},
		rows() {
			return this.data?.map((r) => Object.values(r))
		},
	},
}
</script>
