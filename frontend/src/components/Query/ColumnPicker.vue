<template>
	<div class="flex flex-1 flex-col px-4 pb-4">
		<div v-if="!adding_column && !editing_column" class="mb-4 flex items-center justify-between">
			<div class="text-lg font-medium">Dimension & Metrics</div>
			<Button icon="plus" @click="adding_column = true"></Button>
		</div>
		<div v-if="adding_column || editing_column">
			<div class="mb-4 flex h-7 items-center">
				<Button icon="chevron-left" class="mr-2" @click="reset_new_column"> </Button>
				<div class="text-lg font-medium">{{ editing_column ? 'Edit' : 'Add' }} {{ new_column_type }}</div>
			</div>
			<div class="flex flex-col space-y-3">
				<div class="flex h-9 items-center space-x-2 rounded-md border bg-gray-50 p-0.5 text-sm">
					<div
						class="flex h-full flex-1 items-center justify-center rounded-md font-light"
						:class="{ 'border bg-white font-normal shadow-sm': new_column_type == 'Metric' }"
						@click.prevent.stop="new_column_type = 'Metric'"
					>
						Metric
					</div>
					<div
						class="flex h-full flex-1 items-center justify-center rounded-md"
						:class="{ 'border bg-white font-normal shadow-sm': new_column_type == 'Dimension' }"
						@click.prevent.stop="new_column_type = 'Dimension'"
					>
						Dimension
					</div>
					<div
						class="flex h-full flex-1 items-center justify-center rounded-md"
						:class="{ 'border bg-white font-normal shadow-sm': new_column_type == 'Expression' }"
						@click.prevent.stop="new_column_type = 'Expression'"
					>
						Expression
					</div>
				</div>
				<MetricPicker
					v-if="new_column_type == 'Metric'"
					:column="edit_column"
					:query="query"
					@column-select="add_update_column"
				/>
				<DimensionPicker
					v-if="new_column_type == 'Dimension'"
					:column="edit_column"
					:query="query"
					@column-select="add_update_column"
				/>
				<div v-if="new_column_type == 'Expression'" class="text-center text-gray-500">Coming Soon...</div>
			</div>
		</div>
		<div
			v-if="columns.length == 0 && !adding_column && !editing_column"
			class="flex flex-1 items-center justify-center rounded-md border-2 border-dashed border-gray-200 text-sm font-light text-gray-400"
		>
			<p>No columns selected</p>
		</div>
		<div
			v-else-if="columns.length > 0 && !adding_column && !editing_column"
			class="flex flex-1 select-none flex-col overflow-scroll scrollbar-hide"
		>
			<Draggable v-model="columns" group="columns" item-key="name" @sort="update_column_order">
				<template #item="{ element: column }">
					<div
						class="flex h-10 cursor-pointer items-center justify-between space-x-8 border-b text-sm text-gray-600 last:border-0 hover:bg-gray-50"
						@click.prevent.stop="
							() => {
								edit_column = column
								editing_column = true
								new_column_type = column.aggregation == 'Group By' ? 'Dimension' : 'Metric'
							}
						"
					>
						<div class="flex items-center">
							<DragHandleIcon class="mr-1 -ml-1 h-4 w-4 rotate-90 cursor-grab self-center text-gray-400" />
							<span
								v-if="column.aggregation"
								class="my-0 mr-2 flex-1 select-none whitespace-nowrap rounded border border-orange-200 px-1 py-0.5 text-xs text-orange-400/80"
							>
								{{ column.aggregation }}
							</span>
							<span class="text-base font-medium">{{ column.label }}</span>
						</div>
						<div class="flex items-center">
							<div class="mr-1 font-light text-gray-500">{{ column.table_label }}</div>
							<div
								class="flex items-center px-1 py-0.5 text-gray-500 hover:text-gray-600"
								@click.prevent.stop="query.remove_column.submit({ column })"
							>
								<FeatherIcon name="x" class="h-3 w-3" />
							</div>
						</div>
					</div>
				</template>
			</Draggable>
		</div>
	</div>
</template>

<script>
import Draggable from 'vuedraggable'
import ColumnSearch from '@/components/Query/ColumnSearch.vue'
import DragHandleIcon from '@/components/DragHandleIcon.vue'
import ColumnMenu from '@/components/Query/ColumnMenu.vue'
import MetricPicker from '@/components/Query/MetricPicker.vue'
import DimensionPicker from '@/components/Query/DimensionPicker.vue'

export default {
	name: 'ColumnPicker',
	props: ['query'],
	components: {
		Draggable,
		ColumnSearch,
		DragHandleIcon,
		ColumnMenu,
		MetricPicker,
		DimensionPicker,
	},
	data() {
		return {
			adding_column: false,
			edit_column: null,
			editing_column: false,
			new_column_type: 'Metric',
		}
	},
	computed: {
		tables() {
			return this.query.doc.tables
		},
		columns() {
			return this.query.doc.columns
		},
	},
	methods: {
		update_column_order(e) {
			if (e.oldIndex != e.newIndex) {
				this.query.move_column.submit({
					from_index: e.oldIndex,
					to_index: e.newIndex,
				})
			}
		},
		add_update_column(column) {
			if (this.adding_column) {
				this.query.add_column.submit({ column })
			} else if (this.editing_column) {
				this.query.update_column.submit({ column })
			}
			this.reset_new_column()
		},
		reset_new_column() {
			this.new_column_type = 'Metric'
			this.adding_column = false
			this.editing_column = false
			this.edit_column = null
		},
	},
}
</script>
