<template>
	<div class="flex h-full min-h-[12rem] flex-1 py-4">
		<div class="flex w-1/4 flex-shrink-0 flex-col justify-between space-y-3 border-r pr-4">
			<div class="space-y-3">
				<div class="space-y-2 text-gray-600">
					<div class="text-base font-light text-gray-500">Chart Title</div>
					<Input type="text" placeholder="Enter chart title..." v-model="unsaved_chart.title" />
				</div>
				<div class="space-y-2">
					<div class="text-base font-light text-gray-500">Select Chart Type</div>
					<div class="-ml-1 grid grid-cols-[repeat(auto-fill,3.5rem)] gap-3">
						<div
							class="flex flex-col items-center space-y-1 text-gray-500"
							:class="{
								'cursor-pointer hover:text-gray-600': !invalid_chart_types.includes(chart.name),
								'cursor-not-allowed hover:text-gray-500': invalid_chart_types.includes(chart.name),
							}"
							v-for="(chart, i) in chart_types"
							:key="i"
							@click="set_chart_type(chart.name)"
						>
							<div
								class="flex h-12 w-12 items-center justify-center rounded-md border border-gray-200 bg-white hover:shadow"
								:class="{
									' border-blue-300 text-blue-500 shadow-sm hover:shadow-sm': chart.name == unsaved_chart.type,
									' border-dashed border-gray-300 opacity-60 hover:shadow-none': invalid_chart_types.includes(
										chart.name
									),
								}"
							>
								<FeatherIcon :name="chart.icon" class="h-6 w-6" />
							</div>
							<span
								class="text-sm"
								:class="{
									'font-normal text-blue-600': chart.name == unsaved_chart.type,
									'font-light': chart.name != unsaved_chart.type,
									'opacity-60': invalid_chart_types.includes(chart.name),
								}"
							>
								{{ chart.name }}
							</span>
						</div>
					</div>
				</div>
				<div class="space-y-2 text-gray-600">
					<div class="text-base font-light text-gray-500">Select Dimension</div>
					<Input type="select" v-model="unsaved_chart.label_column" :options="label_columns" />
				</div>
				<div class="space-y-2 text-gray-600">
					<div class="text-base font-light text-gray-500">Select Measure</div>
					<Input type="select" v-model="unsaved_chart.value_column" :options="value_columns" />
				</div>
			</div>
			<div>
				<button
					class="w-full rounded-md bg-gray-100 py-1.5 text-lg text-gray-500"
					:class="{ 'cursor-pointer bg-blue-500 text-white hover:bg-blue-600': !save_disabled }"
					@click="save_chart"
				>
					Save Changes
				</button>
			</div>
		</div>
		<div class="flex-1" ref="chart_container"></div>
	</div>
</template>

<script>
import { Chart } from 'frappe-charts'

export default {
	name: 'QueryVisualizer',
	props: ['query'],
	data() {
		return {
			unsaved_chart: {
				query: this.query.doc.name,
				title: this.query.doc.title,
				type: '',
				label_column: '',
				value_column: '',
			},
			chart_types: [
				{
					name: 'Bar',
					icon: 'bar-chart-2',
				},
				{
					name: 'Line',
					icon: 'trending-up',
				},
				{
					name: 'Pie',
					icon: 'pie-chart',
				},
				{
					name: 'Row',
					icon: 'align-left',
				},
				{
					name: 'Funnel',
					icon: 'filter',
				},
			],
			chart: undefined,
			chart_name: undefined,
		}
	},
	resources: {
		query_chart() {
			return {
				method: 'analytics.api.get_query_chart',
				params: {
					query: this.query.doc.name,
				},
				auto: true,
				onSuccess(chart) {
					if (chart) {
						const { name, title, type, label_column, value_column } = chart
						this.chart_name = name
						Object.assign(this.unsaved_chart, {
							title,
							type,
							label_column,
							value_column,
						})
					}
				},
			}
		},
		create_chart: {
			method: 'analytics.api.create_query_chart',
		},
		update_chart: {
			method: 'analytics.api.update_query_chart',
		},
	},
	mounted() {
		this.render_chart()
	},
	computed: {
		result() {
			return JSON.parse(this.query.doc.result || '[]')
		},
		label_columns() {
			return [''].concat(this.query.doc.columns.filter((c) => c.aggregation == 'Group By').map((c) => c.label))
		},
		value_columns() {
			return [''].concat(this.query.doc.columns.filter((c) => c.aggregation != 'Group By').map((c) => c.label))
		},
		invalid_chart_types() {
			return ['Funnel', 'Row']
		},
		save_disabled() {
			const { title, type, label_column, value_column } = this.unsaved_chart
			const query_chart = this.$resources.query_chart.data

			return (
				query_chart &&
				query_chart.title == title &&
				query_chart.type == type &&
				query_chart.label_column == label_column &&
				query_chart.value_column == value_column
			)
		},
	},
	watch: {
		unsaved_chart: {
			handler() {
				this.render_chart()
			},
			deep: true,
		},
	},
	methods: {
		set_chart_type(chart_type) {
			if (this.invalid_chart_types.includes(chart_type)) {
				return
			}
			this.unsaved_chart.type = chart_type
		},
		render_chart() {
			if (!this.result.length) {
				return
			}

			switch (this.unsaved_chart.type) {
				case 'Line':
				case 'Bar':
				case 'Pie':
					this.rende_single_value_chart(this.unsaved_chart.type)
					break

				default:
					break
			}
		},
		rende_single_value_chart(type) {
			if (!this.unsaved_chart.label_column || !this.unsaved_chart.value_column) {
				return
			}

			const data = this.result.slice(1)
			const label_column_idx = this.query.doc.columns.findIndex((c) => c.label == this.unsaved_chart.label_column)
			const value_column_idx = this.query.doc.columns.findIndex((c) => c.label == this.unsaved_chart.value_column)

			let label_value_map = data.map((row) => ({
				label: row[label_column_idx],
				value: row[value_column_idx],
			}))
			if (type == 'Pie') {
				// explicitly sort data in case of Pie chart
				label_value_map = label_value_map.sort((a, b) => b.value - a.value)
			}

			this.chart = new Chart(this.$refs.chart_container, {
				type: type.toLowerCase(),
				height: this.$refs.chart_container.clientHeight,
				data: {
					labels: label_value_map.map((row) => row.label),
					datasets: [{ values: label_value_map.map((row) => row.value) }],
				},
			})
		},
		save_chart() {
			const query = this.query.doc.name
			const chart_name = this.chart_name
			const { title, type, label_column, value_column } = this.unsaved_chart
			if (chart_name) {
				this.$resources.update_chart.submit(
					{
						chart_name,
						title,
						type,
						label_column,
						value_column,
					},
					{
						onSuccess: () => {
							this.$resources.query_chart.fetch()
							this.$notify({
								title: 'Chart Updated',
								color: 'green',
								icon: 'check',
							})
						},
						onError: () => {
							this.$notify({
								title: 'Something went wrong',
								color: 'red',
								icon: 'alert-circle',
							})
						},
					}
				)
			} else if (title && type && label_column && value_column) {
				this.$resources.create_chart.submit(
					{
						query,
						title,
						type,
						label_column,
						value_column,
					},
					{
						onSuccess: () => {
							this.$resources.query_chart.fetch()
							this.$notify({
								title: 'Chart Created',
								color: 'green',
								icon: 'check',
							})
						},
						onError: () => {
							this.$notify({
								title: 'Something went wrong',
								color: 'red',
								icon: 'alert-circle',
							})
						},
					}
				)
			}
		},
	},
}
</script>
