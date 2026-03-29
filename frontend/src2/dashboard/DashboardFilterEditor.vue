<script setup lang="ts">
import { IconPicker } from 'frappe-ui/icons'
import { computed, inject, reactive, ref } from 'vue'
import useChart from '../charts/chart'
import { copy } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import ColumnFilterValueSelector from '../query/components/ColumnFilterValueSelector.vue'
import { getOperatorOptions, getValueSelectorType } from '../query/components/filter_utils'
import NumberFilterPicker from '../query/components/NumberFilterPicker.vue'
import RelativeDatePicker from '../query/components/RelativeDatePicker.vue'
import { ColumnOption, FilterOperator } from '../types/query.types'
import { WorkbookDashboardFilter } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import { __ } from '../translation'
import { Switch, Tabs, DatePicker, DateRangePicker } from 'frappe-ui'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardFilter }>()

const filter = reactive(copy(props.item))
if (!filter.links) {
	filter.links = {}
}

const tabIndex = ref(0)
const tabs = [
	{
		label: __('Setup'),
		value: 'setup',
	},
	{
		label: __('Config'),
		value: 'config',
	},
]

const charts = computed(() => {
	return dashboard.doc.items
		.filter((i) => i.type === 'chart')
		.map((i) => i.chart)
		.filter(Boolean)
})

const queries = computed(() => {
	return charts.value
		.map((c) => useChart(c).getDependentQueries())
		.flat()
		.filter((q, i, self) => self.findIndex((qq) => qq === q) === i)
		.filter(Boolean) as string[]
})

const linkOptions = computed(() => {
	return charts.value.map((c) => {
		const chart = useChart(c)
		const dependentColumns = chart.getDependentQueryColumns().map((group) => {
			return {
				...group,
				items: disableColumnOptions(group.items),
			}
		})
		return {
			name: chart.doc.name,
			title: chart.doc.title,
			columns: dependentColumns,
		}
	})
})

const enabledLinks = computed(() => Object.keys(filter.links))
function toggleLink(link: string) {
	if (enabledLinks.value.includes(link)) {
		delete filter.links[link]
	} else {
		filter.links[link] = ''
	}
}

const FILTER_TYPES = {
	String: FIELDTYPES.TEXT,
	Number: FIELDTYPES.NUMBER,
	Date: FIELDTYPES.DATE,
}
function disableColumnOptions(options: ColumnOption[]) {
	return options.map((o) => {
		return {
			...o,
			disabled: !FILTER_TYPES[filter.filter_type].includes(o.data_type),
		}
	})
}

function onFilterTypeChange() {
	filter.default_operator = undefined
	filter.default_value = undefined
	filter.links = {}
}

const defaultOperatorOptions = computed(() => getOperatorOptions(filter.filter_type))

const defaultValueSelectorType = computed(() => {
	if (!filter.default_operator) return
	return getValueSelectorType(filter.default_operator, filter.filter_type)
})

function onDefaultOperatorChange(operator: FilterOperator) {
	const oldType = defaultValueSelectorType.value
	filter.default_operator = operator
	if (oldType !== getValueSelectorType(operator, filter.filter_type)) {
		filter.default_value = undefined
	}
}

function clearDefault() {
	filter.default_operator = undefined
	filter.default_value = undefined
}

const sourceColumn = computed(() => {
	const firstChart = Object.keys(filter.links)[0]
	if (!firstChart) return
	const linkedColumn = filter.links[firstChart]
	return dashboard.getColumnFromFilterLink(linkedColumn)
})

function defaultValuesProvider(search: string) {
	if (!sourceColumn.value) return Promise.resolve([])
	return dashboard.getDistinctColumnValues(
		sourceColumn.value.query,
		sourceColumn.value.column,
		search,
	)
}

const editDisabled = computed(() => {
	return (
		!filter.filter_name ||
		!filter.filter_type ||
		JSON.stringify(filter) === JSON.stringify(props.item)
	)
})

function saveEdit() {
	Object.assign(props.item, filter)
}
</script>

<template>
	<Dialog
		:modelValue="dashboard.isEditingItem(props.item)"
		@update:modelValue="!$event ? (dashboard.editingItemIndex = undefined) : true"
		:options="{
			title: __('Edit Filter'),
			actions: [
				{
					label: __('Save'),
					variant: 'solid',
					disabled: editDisabled,
					onClick: saveEdit,
				},
				{
					label: __('Cancel'),
					onClick: () => (dashboard.editingItemIndex = undefined),
				},
			],
		}"
	>
		<template #body-content>
			<div class="flex flex-col min-h-[20rem] max-h-[20rem]">
				<Tabs v-model="tabIndex" :tabs="tabs" class="-mt-6">
					<template #tab-panel="{ tab }">
						<div v-if="tab.value === 'setup'" class="flex flex-col gap-4 pt-2">
							<div class="flex items-end gap-1.5 p-1">
								<FormControl
									class="flex-1"
									:label="__('Label')"
									v-model="filter.filter_name"
									:placeholder="__('Enter filter label...')"
									autocomplete="off"
								/>
								<FormControl
									class="flex-1 flex-shrink-0"
									v-model="filter.filter_type"
									:label="__('Type')"
									type="select"
									:options="Object.keys(FILTER_TYPES)"
									@update:modelValue="onFilterTypeChange"
								/>
							</div>
							<div class="flex flex-col gap-1 border-t pt-3">
								<label class="text-xs text-ink-gray-5">{{
									__('Linked Charts')
								}}</label>
								<div
									v-for="link in linkOptions"
									:key="link.name"
									class="flex h-8 w-full items-center gap-2"
								>
									<Switch
										size="sm"
										:modelValue="enabledLinks.includes(link.name)"
										@update:modelValue="toggleLink(link.name)"
									></Switch>
									<p class="flex-1 truncate text-base">{{ link.title }}</p>
									<div
										v-if="enabledLinks.includes(link.name)"
										class="ml-auto flex-shrink-0"
									>
										<Autocomplete
											class="min-w-[10rem]"
											:placeholder="__('Select a column')"
											:options="link.columns"
											:modelValue="filter.links[link.name]"
											@update:modelValue="
												filter.links[link.name] = $event.value
											"
										/>
									</div>
								</div>
							</div>
						</div>
						<div v-else-if="tab.value === 'config'" class="flex flex-col gap-4 pt-2">
							<div class="flex flex-col gap-1.5 p-1">
								<label class="block text-xs text-ink-gray-5">{{
									__('Filter Icon')
								}}</label>
								<IconPicker v-model="filter.icon" />
							</div>
							<div
								v-if="filter.filter_type"
								class="flex flex-col gap-2.5 border-t pt-3 p-1"
							>
								<div class="flex items-center justify-between">
									<label class="text-xs text-ink-gray-5">{{
										__('Default Value')
									}}</label>
									<button
										v-if="filter.default_operator"
										class="text-xs text-ink-gray-5 hover:text-ink-gray-7"
										@click="clearDefault"
									>
										{{ __('Clear') }}
									</button>
								</div>
								<NumberFilterPicker
									v-if="filter.filter_type === 'Number'"
									v-model:operator="filter.default_operator"
									v-model:value="filter.default_value as number"
								/>
								<template v-else>
									<div class="flex gap-2 items-start">
										<FormControl
											type="select"
											:placeholder="__('Select operator...')"
											:modelValue="filter.default_operator"
											:options="defaultOperatorOptions"
											@update:modelValue="onDefaultOperatorChange($event)"
										/>
										<template v-if="defaultValueSelectorType">
											<DatePicker
												v-if="defaultValueSelectorType === 'date'"
												class="flex-1"
												:modelValue="filter.default_value as string"
												@update:modelValue="filter.default_value = $event"
											/>
											<DateRangePicker
												v-else-if="
													defaultValueSelectorType === 'date_range'
												"
												class="flex-1"
												:range="true"
												v-model="filter.default_value as string[]"
											/>
											<RelativeDatePicker
												v-else-if="
													defaultValueSelectorType === 'relative_date'
												"
												class="flex-1"
												v-model="filter.default_value as string"
											/>
											<div
												v-else-if="defaultValueSelectorType === 'select'"
												class="flex-1"
											>
												<ColumnFilterValueSelector
													v-model="filter.default_value as string[]"
													:valuesProvider="defaultValuesProvider"
												/>
											</div>
											<FormControl
												v-else-if="defaultValueSelectorType === 'text'"
												class="flex-1"
												v-model="filter.default_value"
												:placeholder="__('Value')"
												autocomplete="off"
											/>
										</template>
									</div>
								</template>
							</div>
						</div>
					</template>
				</Tabs>
			</div>
		</template>
	</Dialog>
</template>

<style scoped>
:deep([role='tablist']) {
	padding-bottom: 0;
	gap: 1rem;
}
</style>
