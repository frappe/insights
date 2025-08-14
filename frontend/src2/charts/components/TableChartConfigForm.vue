<script setup lang="ts">
import { computed, provide, ref, watchEffect } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { FIELDTYPES } from '../../helpers/constants'
import { TableChartConfig } from '../../types/chart.types'
import { ColumnOption, DimensionDataType, DimensionOption } from '../../types/query.types'
import CollapsibleSection from './CollapsibleSection.vue'
import DimensionPicker from './DimensionPicker.vue'
import MeasurePicker from './MeasurePicker.vue'
import { useFormatStore } from '../../stores/formatStore'
import ConditonalFormattingDialog from '../../query/components/ConditonalFormattingDialog.vue'
import { FormatGroupArgs, FormattingMode } from '../../query/components/formatting_utils'
import { Plus, Edit, Trash2 } from 'lucide-vue-next'
import { Badge, Button, FormControl } from 'frappe-ui'
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
const formatStore = useFormatStore()

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
	// init format
	if (config.value.conditional_formatting) {
		formatStore.setFormatting(config.value.conditional_formatting)
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

const selectedColumns = computed(() => {
	const columns = new Set<string>()
	config.value.rows?.forEach((row) => {
		if (row.column_name) {
			columns.add(row.column_name)
		}
	})

	config.value.columns?.forEach((col) => {
		if (col.column_name) {
			columns.add(col.column_name)
		}
	})

	// add columns from values
	config.value.values?.forEach((val) => {
		if ('column_name' in val) {
			columns.add(val.column_name)
		}
	})

	// filter columnOptions to only include selected columns
	return props.columnOptions.filter((option) => columns.has(option.value))
})

function getRuleBadgeTheme(mode: string): string {
	switch (mode) {
		case 'cell_rules':
			return 'blue'
		case 'text_rules':
			return 'green'
		case 'date_rules':
			return 'green'
		case 'rank_rules':
			return 'orange'
		case 'color_scale':
			return 'red'
		default:
			return 'gray'
	}
}

function getRuleTypeLabel(mode: string): string {
	switch (mode) {
		case 'cell_rules':
			return 'Value'
		case 'text_rules':
			return 'Text'
		case 'date_rules':
			return 'Date'
		case 'rank_rules':
			return 'Rank'
		case 'color_scale':
			return 'Color Scale'
		default:
			return mode
	}
}

// description of list item
function getRuleDescription(rule: any): string {
	if (rule.mode === 'color_scale') {
		return `${rule.colorScale} color scale`
	}

	const operator = rule.operator || ''
	const color = rule.color || ''
	const value = rule.value

	const formatDate = (d: any) => {
		const date = new Date(d)
		if (isNaN(date.getTime())) return ''
		return `${String(date.getDate()).padStart(2, '0')}/${String(date.getMonth() + 1).padStart(
			2,
			'0',
		)}/${date.getFullYear()}`
	}

	if (rule.mode === 'text_rules') {
		return `Text ${operator} "${value ?? ''}" → ${color}`
	}
	if (rule.mode === 'date_rules') {
		let formatted = ''
		if (Array.isArray(value)) {
			formatted = value.map(formatDate).join(' - ')
		} else if (value) {
			formatted = formatDate(value)
		}
		return `Date ${operator} ${formatted} → ${color}`
	}
	return `${operator} ${value ?? ''} → ${color}`
}

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

function removeRule(index: number) {
	if (config.value.conditional_formatting?.formats) {
		config.value.conditional_formatting.formats.splice(index, 1)
		formatStore.setFormatting(config.value.conditional_formatting)
	}
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
		formatStore.setFormatting(config.value.conditional_formatting)
		editingRuleIndex.value = null
		editingRule.value = null
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
					/>
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
	<!-- todo: make items sortable -->
	<CollapsibleSection title="Conditional Formatting" collapsed>
		<template #title-suffix v-if="config.conditional_formatting?.formats.length">
			<Badge size="[sm]" theme="orange" class="mt-0.5">
				<span class="tnum"> {{ config.conditional_formatting.formats.length }}</span>
			</Badge>
		</template>
		<div v-if="config.conditional_formatting?.formats.length" class="mb-4 space-y-2">
			<div
				v-for="(rule, index) in config.conditional_formatting.formats"
				:key="index"
				class="flex items-center justify-between p-2 bg-gray-50 rounded-lg border"
			>
				<div class="flex flex-col gap-1 flex-1 justify-betweentruncate">
					<div class="text-base font-medium truncate">
						{{ rule.column?.column_name }}
					</div>

					<div class="text-p-xs text-gray-600">{{ getRuleDescription(rule) }}</div>
					<div>
						<Badge
							:label="getRuleTypeLabel(rule.mode)"
							size="sm"
							variant="outline"
							:theme="getRuleBadgeTheme(rule.mode)"
						/>
					</div>
				</div>
				<div class="flex items-center gap-1">
					<Button variant="ghost" size="sm" @click="editRule(index)">
						<template #icon>
							<Edit class="h-4 w-4 text-[#585858]" stroke-width="1.5" />
						</template>
					</Button>
					<Button variant="ghost" size="sm" @click="removeRule(index)">
						<template #icon>
							<Trash2 class="h-4 w-4 text-[#FC7474]" stroke-width="1.5" />
						</template>
					</Button>
				</div>
			</div>
		</div>

		<Button class="w-full" @click="addNewRule">
			<template #prefix>
				<Plus class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
			Add Format
		</Button>
	</CollapsibleSection>

	<ConditonalFormattingDialog
		v-if="showFormatSelectorDialog"
		v-model="showFormatSelectorDialog"
		:column-options="selectedColumns"
		:initial-rule="editingRule"
		:selector-key="editingRuleIndex ?? 'new'"
		@select="handleFormatSelect"
	/>
</template>
editing rule index should pass the cached values(if exists) of the formatGroup to the formatRule
input
