<template>
	<div class="flex h-full min-h-[12rem] w-full flex-1 py-4">
		<div class="flex h-full w-1/4 flex-shrink-0 flex-col space-y-3 border-r pr-4">
			<div class="space-y-2 text-gray-600">
				<div class="text-sm font-light text-gray-500">Select Transform Type</div>
				<Input type="select" v-model="transform_type" :options="transform_type_options" />
			</div>

			<div v-if="transform_type == 'Pivot'" class="space-y-2">
				<div class="space-y-2 text-gray-600">
					<div class="text-sm font-light text-gray-500">Select Pivot Column</div>
					<Input type="select" v-model="pivot_column" :options="pivot_column_options" />
				</div>
			</div>

			<Button appearance="white" @click="apply_transform" :loading="query.apply_transform.loading"> Apply </Button>
		</div>
		<div class="flex w-3/4 pl-4">
			<div
				v-if="!query.doc.transform_result"
				class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
			>
				<p>Apply transform to view result</p>
			</div>
			<div v-else class="flex h-full w-full flex-1 select-text flex-col rounded-md text-base">
				<div class="relative flex-1 overflow-scroll rounded-md border scrollbar-hide">
					<div v-html="query.doc.transform_result" class="w-full"></div>
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
			transform_type: null,
			pivot_column: null,
		}
	},
	mounted() {
		this.load_transform_data()
	},
	computed: {
		transform_type_options() {
			return ['', 'Pivot']
		},
		group_by_columns() {
			return this.query.doc.columns.filter((c) => c.aggregation == 'Group By')
		},
		pivot_column_options() {
			return [''].concat(this.group_by_columns.map((c) => c.label))
		},
		save_disabled() {
			return false
		},
		transform_data() {
			return JSON.parse(this.query.doc.transform_data || {})
		},
	},
	methods: {
		load_transform_data() {
			if (this.query.doc.transform_type) {
				this.transform_type = this.query.doc.transform_type
				if (this.transform_type == 'Pivot') {
					this.pivot_column = this.transform_data.pivot_columns[0]
				}
			}
		},
		validate_transform() {
			if (!this.transform_type) {
				this.$notify({
					title: 'Select a Transform Type',
					color: 'yellow',
					icon: 'alert-circle',
				})
			}

			if (this.transform_type == 'Pivot' && !this.pivot_column) {
				this.$notify({
					title: 'Select a Pivot Column',
					color: 'yellow',
					icon: 'alert-circle',
				})
			}

			return true
		},
		apply_transform() {
			if (!this.validate_transform()) {
				return
			}

			this.query.apply_transform.submit({
				type: this.transform_type,
				data: this.get_transform_data(),
			})
		},
		get_transform_data() {
			switch (this.transform_type) {
				case 'Pivot':
					return this.get_pivot_data()
				default:
					return {}
			}
		},
		get_pivot_data() {
			return {
				index_columns: this.group_by_columns.filter((c) => c.label !== this.pivot_column).map((c) => c.label),
				pivot_columns: [this.pivot_column],
			}
		},
	},
}
</script>

<style lang="postcss">
.dataframe th {
	@apply whitespace-nowrap border-r border-b bg-gray-50 py-2 px-4 text-left text-sm font-medium text-gray-700;
}

.dataframe td {
	@apply whitespace-nowrap border-r border-b bg-white py-2 px-4 text-right text-sm text-gray-700;
}

.dataframe tr > th:first-child {
	@apply sticky left-0;
}
</style>
