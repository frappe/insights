<script setup lang="ts">
import { Plus, X } from 'lucide-vue-next'
import { Badge, Button, FormControl } from 'frappe-ui'
import { computed, ref, watchEffect } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { FIELDTYPES } from '../../helpers/constants'
import ConditonalFormattingDialog from '../../query/components/ConditonalFormattingDialog.vue'
import DataTypeIcon from '../../query/components/DataTypeIcon.vue'
import { FormatGroupArgs, FormattingMode } from '../../query/components/formatting_utils'
import { TableChartConfig } from '../../types/chart.types'
import { ColumnOption, DimensionDataType, DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'
import { wheneverChanges } from '../../helpers'
const props = defineProps<{
	formatGroup?: FormatGroupArgs
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
}>()

const emit = defineEmits({ select: (args: FormatGroupArgs) => true })

const config = defineModel<TableChartConfig>({
	required: true,
	default: () => ({
		rows: [],
		columns: [],
		values: [],
		enable_color_scale: false,
	}),
})

const showFormatSelectorDialog = ref(false)
const editingRuleIndex = ref<number | null>(null)
const editingRule = ref<FormattingMode | null>(null)

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
		}))
)

const dimensions = computed(() => [...props.dimensions, ...measuresAsDimensions.value])

function toColumnOption(item: any, label: string, value: string, dataType: string) {
	return {
		query: '',
		label: item[label],
		data_type: item[dataType],
		value: item[value],
		description: item[dataType],
	}
}

const measuresAndDimensions = computed(() => {
	const measures = config.value.values
		.filter((m) => m?.measure_name)
		.map((m) => toColumnOption(m, 'measure_name', 'measure_name', 'data_type'))

	const dimensions = config.value.columns
		.filter((column) => column?.column_name)
		.map((column) => toColumnOption(column, 'column_name', 'column_name', 'data_type'))

	const rows = config.value.rows
		.filter((row) => row?.dimension_name)
		.map((row) => toColumnOption(row, 'dimension_name', 'dimension_name', 'data_type'))

	return [...measures, ...dimensions, ...rows]
})

const colOptions = computed(() => (measuresAndDimensions.value as ColumnOption[]) || [])

function editRule(index: number) {
	const ruleToEditValue = config.value.conditional_formatting?.formats[index]

	if (ruleToEditValue) {
		editingRule.value = ruleToEditValue as FormattingMode
		editingRuleIndex.value = index
		showFormatSelectorDialog.value = true
	}
}

function addNewRule() {
	editingRuleIndex.value = null
	editingRule.value = null
	showFormatSelectorDialog.value = true
}

function handleFormatSelect(formatGroup: FormatGroupArgs) {
	const newRule = formatGroup.formats[0]
	if (newRule && newRule.column?.column_name) {
		if (!config.value.conditional_formatting) {
			config.value.conditional_formatting = { formats: [], columns: [] }
		}
		const editIndex = editingRuleIndex.value
		if (editIndex !== null) {
			config.value.conditional_formatting.formats[editIndex] = newRule
		} else {
			//add new rule
			config.value.conditional_formatting.formats.push(newRule)
		}
		editingRuleIndex.value = null
		editingRule.value = null
	}
}

function getColumnType(column_name: string) {
	const column = measuresAndDimensions.value.find((column) => column.data_type === column_name)
	if (!column) {
		return 'String'
	}
	return column.data_type
}

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
								:modelValue="config.sticky_columns?.includes(item.dimension_name)"
								@update:modelValue="toggleStickyColumn(item.dimension_name, $event)"
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
			<Toggle label="Compact Number Format" v-model="config.compact_numbers" />
			<Toggle
				v-if="config.values.length === 1"
				label="Show Color Scale"
				v-model="config.enable_color_scale"
			/>
		</div>
	</CollapsibleSection>
	<CollapsibleSection title="Formatting Rules" collapsed>
		<template #title-suffix v-if="config.conditional_formatting?.formats.length">
			<Badge theme="orange">
				<span class="tnum"> {{ config.conditional_formatting.formats.length }}</span>
			</Badge>
		</template>
		<div class="flex flex-col gap-2">
			<div v-if="config.conditional_formatting?.formats.length" class="flex flex-col gap-1">
				<div
					v-for="(rule, idx) in config.conditional_formatting?.formats"
					:key="idx"
					class="flex rounded"
				>
					<div class="flex-1 overflow-hidden">
						<Button
							class="w-full !justify-start rounded-r-none [&>span]:truncate"
							@click="editRule(idx)"
						>
							<template #prefix>
								<DataTypeIcon
									:column-type="getColumnType(rule.column?.column_name)"
								/>
							</template>
							{{ rule.column?.column_name }}
						</Button>
					</div>
					<Button
						class="flex-shrink-0 rounded-l-none border-l"
						@click="config.conditional_formatting.formats.splice(idx, 1)"
					>
						<template #icon>
							<X class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
				</div>
			</div>

			<Button class="w-full" @click="addNewRule">
				<template #prefix>
					<Plus class="h-4 w-4 text-gray-700" stroke-width="1.5" />
				</template>
				Add Rule
			</Button>
		</div>
	</CollapsibleSection>

	<ConditonalFormattingDialog
		v-if="showFormatSelectorDialog"
		v-model="showFormatSelectorDialog"
		:column-options="colOptions"
		:initial-rule="editingRule"
		:selector-key="editingRuleIndex ?? 'new'"
		@select="handleFormatSelect"
	/>
</template>
