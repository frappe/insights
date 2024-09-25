<script setup lang="ts">
import { XIcon } from 'lucide-vue-next'
import { TableChartConfig } from '../../types/chart.types'
import { DimensionOption, MeasureOption } from './ChartConfigForm.vue'
import CollapsibleSection from './CollapsibleSection.vue'

const props = defineProps<{
	dimensions: DimensionOption[]
	measures: MeasureOption[]
}>()

const config = defineModel<TableChartConfig>({
	required: true,
	default: () => ({
		rows: [],
		columns: [],
		values: [],
	}),
})

if (!config.value.rows?.length) {
	config.value.rows = [{} as any]
}
if (!config.value.columns?.length) {
	config.value.columns = [{} as any]
}
if (!config.value.values?.length) {
	config.value.values = [{} as any]
}
</script>

<template>
	<CollapsibleSection title="Rows">
		<div class="flex flex-col gap-2">
			<template v-for="(row, idx) in config.rows" :key="idx">
				<div class="flex items-end gap-1 overflow-hidden">
					<div class="flex-1">
						<Autocomplete
							placeholder="Select a column"
							:showFooter="true"
							:options="props.dimensions"
							:modelValue="row.column_name"
							@update:modelValue="Object.assign(row, $event || {})"
						/>
					</div>
					<Button class="flex-shrink-0" @click="config.rows.splice(idx, 1)">
						<template #icon>
							<XIcon class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
				</div>
			</template>
			<button
				class="text-left text-xs text-gray-600 hover:underline"
				@click="config.rows.push({} as any)"
			>
				+ Add Row
			</button>
		</div>
	</CollapsibleSection>
	<CollapsibleSection title="Columns">
		<div class="flex flex-col gap-2">
			<template v-for="(col, idx) in config.columns" :key="idx">
				<div class="flex items-end gap-1 overflow-hidden">
					<div class="flex-1">
						<Autocomplete
							placeholder="Select a column"
							:showFooter="true"
							:options="props.dimensions"
							:modelValue="col.column_name"
							@update:modelValue="Object.assign(col, $event || {})"
						/>
					</div>
					<Button class="flex-shrink-0" @click="config.columns.splice(idx, 1)">
						<template #icon>
							<XIcon class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
				</div>
			</template>
			<button
				class="text-left text-xs text-gray-600 hover:underline"
				@click="config.columns.push({} as any)"
			>
				+ Add Column
			</button>
		</div>
	</CollapsibleSection>
	<CollapsibleSection title="Values">
		<div class="flex flex-col gap-3">
			<div class="flex flex-col gap-2">
				<template v-for="(val, idx) in config.values" :key="idx">
					<div class="flex items-end gap-1 overflow-hidden">
						<div class="flex-1">
							<Autocomplete
								placeholder="Select a column"
								:showFooter="true"
								:options="props.measures"
								:modelValue="val.measure_name"
								@update:modelValue="Object.assign(val, $event || {})"
							/>
						</div>
						<Button class="flex-shrink-0" @click="config.values.splice(idx, 1)">
							<template #icon>
								<XIcon class="h-4 w-4 text-gray-700" stroke-width="1.5" />
							</template>
						</Button>
					</div>
				</template>
				<button
					class="text-left text-xs text-gray-600 hover:underline"
					@click="config.values.push({} as any)"
				>
					+ Add Value
				</button>
			</div>
			<Checkbox label="Show Filters" v-model="config.show_filter_row" />
			<Checkbox label="Show Row Totals" v-model="config.show_row_totals" />
			<Checkbox label="Show Column Totals" v-model="config.show_column_totals" />
			<!-- <Checkbox label="Conditional Formatting" v-model="config.conditional_formatting" /> -->
		</div>
	</CollapsibleSection>
</template>
