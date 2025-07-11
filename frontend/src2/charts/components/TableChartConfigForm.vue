<script setup lang="ts">
import { computed, watchEffect } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { FIELDTYPES } from '../../helpers/constants'
import { TableChartConfig } from '../../types/chart.types'
import { ColumnOption, DimensionDataType, DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const config = defineModel<TableChartConfig>({
	required: true,
	default: () => ({
		rows: [],
		columns: [],
		values: [],
	}),
})
watchEffect(() => {
	if (!config.value.rows?.length) {
		config.value.rows = [{} as any]
	}
	if (!config.value.columns?.length) {
		config.value.columns = [{} as any]
	}
	if (!config.value.values?.length) {
		config.value.values = [{} as any]
	}
})

const measuresAsDimensions = computed<DimensionOption[]>(() =>
	props.columnOptions
		.filter((o) => FIELDTYPES.NUMBER.includes(o.data_type))
		.map((o) => ({
			column_name: o.value,
			data_type: o.data_type as DimensionDataType,
			dimension_name: o.label,
			label: o.label,
			value: o.value,
		})),
)

const dimensions = computed(() => [...props.dimensions, ...measuresAsDimensions.value])

function toggleStickyColumn(column_name: string, is_sticky: boolean) {
	if (is_sticky) {
		if (!config.value.sticky_columns) {
			config.value.sticky_columns = []
		}
		if (!config.value.sticky_columns.includes(column_name)) {
			config.value.sticky_columns.push(column_name)
		}
	} else {
		config.value.sticky_columns = config.value.sticky_columns?.filter((c) => c !== column_name)
	}
}
</script>

<template>
	<CollapsibleSection title="Rows">
		<div>
			<DraggableList v-model:items="config.rows" group="rows">
				<template #item="{ item, index }">
					<DimensionPicker
						:options="dimensions"
						:model-value="item"
						@update:model-value="Object.assign(item, $event || {})"
						@remove="config.rows.splice(index, 1)"
					>
						<template #config-fields>
							<Toggle
								label="Pin Column"
								:modelValue="config.sticky_columns?.includes(item.column_name)"
								@update:modelValue="toggleStickyColumn(item.column_name, $event)"
							/>
						</template>
					</DimensionPicker>
				</template>
			</DraggableList>
			<button
				class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
				@click="config.rows.push({} as any)"
			>
				+ Add column
			</button>
		</div>
	</CollapsibleSection>

	<CollapsibleSection title="Columns">
		<div class="flex flex-col gap-3">
			<div>
				<DraggableList v-model:items="config.columns" group="columns">
					<template #item="{ item, index }">
						<DimensionPicker
							:options="props.dimensions"
							:model-value="item"
							@update:model-value="Object.assign(item, $event || {})"
							@remove="config.columns.splice(index, 1)"
						/>
					</template>
				</DraggableList>
				<button
					class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
					@click="config.columns.push({} as any)"
				>
					+ Add column
				</button>
			</div>

			<InlineFormControlLabel
				v-if="config.columns.length"
				class="!w-1/2"
				label="Max Column Values"
			>
				<FormControl
					type="number"
					autocomplete="off"
					:modelValue="config.max_column_values"
					@update:modelValue="config.max_column_values = $event"
				/>
			</InlineFormControlLabel>
		</div>
	</CollapsibleSection>

	<CollapsibleSection title="Values">
		<div class="flex flex-col gap-3">
			<div>
				<DraggableList v-model:items="config.values" group="values">
					<template #item="{ item, index }">
						<MeasurePicker
							:model-value="item"
							:column-options="props.columnOptions"
							@update:model-value="Object.assign(item, $event || {})"
							@remove="config.values.splice(index, 1)"
						/>
					</template>
				</DraggableList>
				<button
					class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
					@click="config.values.push({} as any)"
				>
					+ Add column
				</button>
			</div>
			<Toggle label="Show Filters" v-model="config.show_filter_row" />
			<Toggle label="Show Row Totals" v-model="config.show_row_totals" />
			<Toggle label="Show Column Totals" v-model="config.show_column_totals" />
			<Toggle
				v-if="config.values.length === 1"
				label="Show Color Scale"
				v-model="config.enable_color_scale"
			/>
		</div>
	</CollapsibleSection>
</template>
