<script setup lang="ts">
import { computed, inject, reactive } from 'vue'
import useChart from '../charts/chart'
import { copy } from '../helpers'
import { FIELDTYPES } from '../helpers/constants'
import { ColumnOption } from '../types/query.types'
import { WorkbookDashboardFilter } from '../types/workbook.types'
import { Dashboard } from './dashboard'

const dashboard = inject<Dashboard>('dashboard')!
const props = defineProps<{ item: WorkbookDashboardFilter }>()

const filter = reactive(copy(props.item))
if (!filter.links) {
	filter.links = {}
}

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

const editDisabled = computed(() => {
	return (
		!filter.filter_name ||
		!filter.filter_type ||
		JSON.stringify(filter) === JSON.stringify(props.item)
	)
})

function saveEdit() {
	dashboard.editingItemIndex = null
	Object.assign(props.item, filter)
}
</script>

<template>
	<Dialog
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
						placeholder="Enter filter label..."
						autocomplete="off"
					/>
					<FormControl
						class="flex-1 flex-shrink-0"
						v-model="filter.filter_type"
						label="Type"
						type="select"
						:options="Object.keys(FILTER_TYPES)"
						@update:modelValue="onFilterTypeChange"
					/>
				</div>
				<div class="flex flex-col">
					<div class="mb-1 text-p-sm text-gray-700">Linked Charts</div>
					<div
						v-for="link in linkOptions"
						:key="link.name"
						class="flex h-8 w-full items-center gap-2"
					>
						<Toggle
							size="sm"
							:modelValue="enabledLinks.includes(link.name)"
							@update:modelValue="toggleLink(link.name)"
						></Toggle>
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
