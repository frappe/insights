<template>
	<div class="h-full min-h-[12rem] w-full rounded-md bg-white">
		<div class="flex h-14 flex-shrink-0 items-center text-base text-gray-600">
			<div class="pivot-button">
				<Popover :show="pivot_popup_open">
					<template #target>
						<button
							class="add-table-button select-none rounded-md border border-gray-100 bg-gray-100 px-2.5 py-1 hover:bg-gray-200"
							@click="pivot_popup_open = !pivot_popup_open"
						>
							Pivot
						</button>
					</template>
					<template #content>
						<div class="pivot-popup mt-2 flex origin-top-right rounded-md border bg-white shadow-md">
							<div class="flex min-h-[20rem] min-w-[22rem] flex-1 flex-col space-y-4 p-4 text-base">
								<div class="space-y-2">
									<div class="text-base font-light text-gray-500">Select Pivot Column</div>
									<Input
										type="select"
										v-model="pivot_column"
										:options="[''].concat(group_by_columns.map((c) => c.column))"
									/>
								</div>
							</div>
						</div>
					</template>
				</Popover>
			</div>
		</div>
		<div class="flex h-[calc(100%-3.5rem)]">
			<div
				v-if="!pivot_column"
				class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
			>
				<p>Select a pivot column to display the result</p>
			</div>

			<div v-else class="flex h-full w-full flex-1 select-text flex-col rounded-md text-base">
				<!-- Table -->
				<div class="relative flex-1 overflow-scroll rounded-md border scrollbar-hide">
					<table class="border-separate">
						<thead class="sticky top-0 text-gray-500">
							<tr v-for="(row, idx) in header_rows" :key="idx">
								<th
									class="sticky top-0 flex h-8 w-[3rem] items-center justify-center whitespace-nowrap border-r border-b bg-white px-2 text-center font-normal"
								></th>
								<th
									v-for="column in row"
									:key="column.label"
									:rowspan="column.rowspan"
									:colspan="column.colspan"
									class="h-8 whitespace-nowrap border-r border-b bg-white px-2 text-left font-normal"
								>
									{{ column.label }}
								</th>
							</tr>
						</thead>
						<tbody class="pointer-events-none">
							<tr v-for="(row, i) in data_rows" :key="i">
								<td
									class="sticky left-0 w-[3rem] whitespace-nowrap border-r border-b bg-white p-2 text-center text-gray-500"
								>
									{{ i + 1 }}
								</td>
								<td
									v-for="(cell, j) in row"
									:key="j"
									class="whitespace-nowrap border-r border-b bg-white p-2 pr-4 text-gray-600"
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
	</div>
</template>

<script>
export default {
	name: 'QueryTransform',
	props: ['query'],
	data() {
		return {
			pivot_popup_open: false,
			pivot_column: null,
		}
	},
	mounted() {
		// detect click outside of input
		this.outside_click_listener = (e) => {
			if (e.target.closest('.pivot-button') || e.target.closest('.pivot-popup')) {
				return
			}
			this.pivot_popup_open = false
		}
		document.addEventListener('click', this.outside_click_listener)
	},
	beforeDestroy() {
		document.removeEventListener('click', this.outside_click_listener)
	},
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
		group_by_columns() {
			return this.columns.filter((c) => c.aggregation === 'Group By')
		},
		aggregated_columns() {
			return this.columns.filter((c) => c.aggregation && c.aggregation !== 'Group By')
		},
		header_rows() {
			const group_by_columns = this.group_by_columns.filter((c) => c.column !== this.pivot_column)

			const pivot_values = this.get_values_of_column(this.pivot_column)
			const unique_pivot_values = [...new Set(pivot_values)]

			const aggregated_columns = this.columns.filter((c) => c.aggregation && c.aggregation !== 'Group By')
			const colspan = aggregated_columns.length

			const rowspan = 2
			const header_row_one = [
				...group_by_columns.map((c) => {
					return {
						...c,
						rowspan,
					}
				}),
				...unique_pivot_values.map((c) => {
					return {
						label: c,
						colspan,
					}
				}),
			]

			const header_row_two = unique_pivot_values.reduce((acc, _) => {
				return [...acc, ...aggregated_columns.map((c) => ({ label: c.label }))]
			}, [])

			return [header_row_one, header_row_two]
		},
		data_rows() {
			const pivot_column_idx = this.get_index_of_column(this.pivot_column)
			const pivot_values = this.get_values_of_column(this.pivot_column)
			const unique_pivot_values = [...new Set(pivot_values)]

			const group_by_columns = this.group_by_columns.filter((c) => c.column !== this.pivot_column).map((c) => c.column)
			const group_by_column_indexes = group_by_columns.map((c) => this.get_index_of_column(c))

			const group_by_column_idx = group_by_column_indexes[0]

			const group_by_values = this.data.map((row) => row[group_by_column_idx])
			const unique_group_by_values = [...new Set(group_by_values)]

			const aggregated_columns_indexes = this.aggregated_columns.map((c) => this.get_index_of_column(c.column))

			const new_data = unique_group_by_values.reduce((acc, val) => {
				if (!acc[val]) {
					acc[val] = {}
				}

				unique_pivot_values.forEach((pivot_value) => {
					if (!acc[val][pivot_value]) {
						acc[val][pivot_value] = Array(aggregated_columns_indexes.length).fill('')
					}

					this.data.forEach((row) => {
						if (row[group_by_column_idx] === val && row[pivot_column_idx] === pivot_value) {
							const aggregated_values = aggregated_columns_indexes.map((idx) => row[idx] || '')
							acc[val][pivot_value] = aggregated_values
						}
					})
				})

				return acc
			}, {})

			const new_data_rows = Object.keys(new_data).reduce((acc, key) => {
				let row = [key]
				const pivot_values = Object.keys(new_data[key])
				pivot_values.forEach((pivot_value) => {
					row = [...row, ...new_data[key][pivot_value]]
				})
				acc.push(row)
				return acc
			}, [])

			return new_data_rows
		},
	},
	methods: {
		get_index_of_column(column) {
			return this.columns.findIndex((c) => c.column === column)
		},
		get_values_of_column(column) {
			const idx = this.get_index_of_column(column)
			return this.data.map((row) => row[idx])
		},
	},
}
</script>
