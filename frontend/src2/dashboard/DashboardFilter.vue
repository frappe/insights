<script setup lang="ts">
import { computed, inject, reactive, ref } from 'vue'
import { Chart, getCachedChart } from '../charts/chart'
import { copy, wheneverChanges } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import DataTypeIcon from '../query/components/DataTypeIcon.vue'
import { getCachedQuery, Query } from '../query/query'
import { ColumnDataType, ColumnOption } from '../types/query.types'
import { WorkbookDashboardFilter } from '../types/workbook.types'
import { Dashboard } from './dashboard'
import Filter from './Filter.vue'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardFilter }>()

const filter = ref(copy(props.item))
if (!filter.value.links) {
	filter.value.links = {}
}

const charts = computed(() => {
	return dashboard.doc.items
		.filter((i) => i.type === 'chart')
		.map((i) => i.chart)
		.filter(Boolean)
})

const queries = computed(() => {
	return charts.value
		.map((c) => getCachedChart(c))
		.filter(Boolean)
		.map((c) => c!.getDependentQueries())
		.flat()
		.filter((q, i, self) => self.findIndex((qq) => qq === q) === i)
		.filter(Boolean) as string[]
})

const linkOptions = computed(() => {
	return {
		queries: queries.value
			.map((q) => getCachedQuery(q))
			.filter(Boolean)
			.map((q) => {
				const query = q as Query
				if (!query.result.executedSQL) query.execute()
				return {
					name: query.doc.name,
					title: query.doc.title || query.doc.name,
					columns: disableColumnOptions(query.result.columnOptions),
				}
			}),
		charts: charts.value
			.map((c) => getCachedChart(c))
			.filter(Boolean)
			.map((c) => {
				const chart = c as Chart
				const query = chart.dataQuery
				if (!query.result.executedSQL) query.execute()
				return {
					name: query.doc.name,
					title: chart.doc.title || query.doc.name,
					columns: disableColumnOptions(query.result.columnOptions),
				}
			}),
	}
})

const enabledLinks = computed(() => Object.keys(filter.value.links))
function toggleLink(link: string) {
	if (enabledLinks.value.includes(link)) {
		delete filter.value.links[link]
	} else {
		filter.value.links[link] = ''
	}
}

const filterTypes = {
	String: FIELDTYPES.TEXT,
	Number: FIELDTYPES.NUMBER,
	Date: FIELDTYPES.DATE,
}

function disableColumnOptions(options: ColumnOption[]) {
	return options.map((o) => {
		return {
			...o,
			disabled: !filterTypes[filter.value.filter_type].includes(o.data_type),
		}
	})
}

function onFilterTypeChange() {
	filter.value.default_operator = undefined
	filter.value.default_value = undefined
	filter.value.links = {}
}

const state = reactive({
	operator: filter.value.default_operator,
	value: filter.value.default_value,
})
wheneverChanges(
	() => state,
	() => {
		dashboard.updateFilter(filter.value.filter_name, state.operator, state.value)
		dashboard.refresh()
	},
	{ deep: true }
)
const label = computed(() => {
	let _label = filter.value.filter_name
	if (state.operator && state.value) {
		const value_str = Array.isArray(state.value) ? state.value.join(', ') : state.value
		_label += ` ${state.operator} ${value_str}`
	}
	return _label
})

const editDisabled = computed(() => {
	return (
		!filter.value.filter_name ||
		!filter.value.filter_type ||
		JSON.stringify(filter.value) === JSON.stringify(props.item)
	)
})

function saveEdit() {
	dashboard.editingItemIndex = null
	Object.assign(props.item, filter.value)
}
</script>

<template>
	<div class="h-8 [&>div:first-child]:h-full">
		<Popover class="h-full">
			<template #target="{ togglePopover, isOpen }">
				<Button
					variant="outline"
					class="flex h-full w-full !justify-start shadow-sm"
					@click="togglePopover"
				>
					<template #prefix>
						<DataTypeIcon
							v-if="filter.filter_type"
							:column-type="(filterTypes[filter.filter_type][0] as ColumnDataType)"
							class="h-4 w-4 flex-shrink-0"
							stroke-width="1.5"
						/>
					</template>
					<p class="flex-1 truncate text-sm">
						{{ label || 'Filter' }}
					</p>
				</Button>
			</template>
			<template #body-main="{ togglePopover, isOpen }">
				<div class="w-full p-2">
					<Filter
						v-if="isOpen"
						:filter-type="filter.filter_type"
						v-model:operator="state.operator"
						v-model:value="state.value"
						@update:value="() => togglePopover()"
					>
					</Filter>
				</div>
			</template>
		</Popover>
	</div>

	<Dialog
		v-if="dashboard.isEditingItem(props.item)"
		:modelValue="dashboard.isEditingItem(props.item)"
		@update:modelValue="!$event ? (dashboard.editingItemIndex = null) : true"
		:options="{
			title: 'Edit Filter',
			actions: [
				{
					label: 'Save',
					variant: 'solid',
					disabled: editDisabled,
					onClick: saveEdit,
				},
				{
					label: 'Cancel',
					onClick: () => (dashboard.editingItemIndex = null),
				},
			],
		}"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<div class="flex gap-4">
					<FormControl
						class="flex-1 flex-shrink-0"
						label="Label"
						v-model="filter.filter_name"
						autocomplete="off"
					/>
					<FormControl
						class="flex-1 flex-shrink-0"
						v-model="filter.filter_type"
						label="Type"
						type="select"
						:options="Object.keys(filterTypes)"
						@update:modelValue="onFilterTypeChange"
					/>
				</div>
				<div v-if="filter.filter_type" class="flex w-full flex-col gap-2">
					<label class="block text-xs text-gray-600">Default Value</label>
					<Filter
						class="w-full"
						:filter-type="filter.filter_type"
						v-model:operator="filter.default_operator"
						v-model:value="filter.default_value"
					></Filter>
				</div>
				<div class="flex flex-col">
					<div class="text-p-sm text-gray-700">Linked Queries</div>
					<div
						v-for="link in linkOptions.queries"
						:key="link.name"
						class="flex h-8 w-full items-center gap-2"
					>
						<Checkbox
							size="sm"
							:modelValue="enabledLinks.includes(link.name)"
							@update:modelValue="toggleLink(link.name)"
						></Checkbox>
						<p class="flex-1 truncate text-base">{{ link.title }}</p>
						<div v-if="enabledLinks.includes(link.name)" class="ml-auto flex-shrink-0">
							<Autocomplete
								class="min-w-[10rem]"
								placeholder="Select a column"
								:options="link.columns"
								:modelValue="filter.links[link.name]"
								@update:modelValue="filter.links[link.name] = $event.value"
							/>
						</div>
					</div>
					<div class="mt-2 text-p-sm text-gray-700">Linked Charts</div>
					<div
						v-for="link in linkOptions.charts"
						:key="link.name"
						class="flex h-8 w-full items-center gap-2"
					>
						<Checkbox
							size="sm"
							:modelValue="enabledLinks.includes(link.name)"
							@update:modelValue="toggleLink(link.name)"
						></Checkbox>
						<p class="flex-1 truncate text-base">{{ link.title }}</p>
						<div v-if="enabledLinks.includes(link.name)" class="ml-auto flex-shrink-0">
							<Autocomplete
								class="min-w-[10rem]"
								placeholder="Select a column"
								:options="link.columns"
								:modelValue="filter.links[link.name]"
								@update:modelValue="filter.links[link.name] = $event.value"
							/>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
