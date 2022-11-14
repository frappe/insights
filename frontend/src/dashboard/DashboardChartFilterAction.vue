<script setup>
import { ref, inject, computed, nextTick, watch } from 'vue'
import { safeJSONParse } from '@/utils'

const dashboard = inject('dashboard')
const chart = inject('item')
const filters = ref([
	{
		column: '',
		filter: '',
		columnOptions: [],
	},
])

const allColumns = dashboard.getAllColumns(chart.query)
watch(allColumns, async () => {
	await nextTick()
	const initialFilters = safeJSONParse(chart.chart_filters, []).map((filter) => {
		return {
			column: filter.column,
			filter: filter.filter,
			columnOptions: getColumnOptions(getFilterType(filter.filter.label)),
		}
	})
	filters.value = initialFilters.length ? initialFilters : filters.value
})

const filterOptions = computed(() => dashboard.filters?.map((f) => f.filter_label))

function getFilterType(filter_label) {
	return dashboard.filters.find((f) => `${f.filter_label}` === `${filter_label}`)?.filter_type
}

async function updateColumnOptions(filter) {
	await nextTick()
	const filter_type = getFilterType(filter.filter.label)
	filter.columnOptions = getColumnOptions(filter_type)
}

function getColumnOptions(filter_type) {
	return (
		allColumns.value
			.map((c) => ({
				label: c.label,
				description: `${c.type}`,
				value: `${c.table}.${c.column}`,
				disabled: c.type !== filter_type,
			}))
			// sort enabled options first
			.sort((a, b) => (a.disabled === b.disabled ? 0 : a.disabled ? 1 : -1))
	)
}

function addFilter() {
	filters.value.push({
		column: '',
		filter: '',
		columnOptions: [],
	})
}

const $notify = inject('$notify')
function applyFilter() {
	dashboard.update_chart_filters
		.submit({
			chart: chart.name,
			filters: filters.value.map((f) => ({
				column: f.column,
				filter: f.filter,
			})),
		})
		.then(() => {
			$notify({
				title: 'Dashboard Filter Applied',
				appearance: 'success',
			})
			dashboard.refreshItems()
		})
}

const submitDisabled = computed(() => {
	return filters.value.some((f) => !f.column || !f.filter)
})
</script>

<template>
	<Popover :hideOnBlur="false">
		<template #target="{ togglePopover }">
			<div class="cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100">
				<FeatherIcon
					name="filter"
					class="h-4 w-4"
					@mousedown.prevent.stop=""
					@click="togglePopover()"
				/>
			</div>
		</template>
		<template #body="{ togglePopover }">
			<div
				class="min-w-[24rem] max-w-[40rem] rounded-md border bg-white pt-2 text-base text-gray-800 shadow-md"
			>
				<span class="px-3 text-gray-600">Connect Filters</span>
				<div class="space-y-3 p-3">
					<div
						class="flex items-end space-x-2 text-sm"
						v-for="(filter, index) in filters"
						:key="index"
					>
						<Autocomplete
							class="w-1/2"
							label="Filter"
							:options="filterOptions"
							v-model="filter.filter"
							@selectOption="updateColumnOptions(filter)"
						></Autocomplete>
						<span class="h-6">=</span>
						<Autocomplete
							class="w-1/2"
							label="Column"
							:options="filter.columnOptions"
							v-model="filter.column"
						></Autocomplete>
						<Button
							icon="x"
							appearance="minimal"
							@click.prevent.stop="filters.splice(index, 1)"
						></Button>
					</div>
				</div>
				<div class="flex justify-end space-x-2 border-t p-2">
					<Button iconLeft="plus" @click="addFilter()">Add</Button>
					<Button
						appearance="primary"
						:disabled="submitDisabled"
						@click="
							() => {
								applyFilter()
								togglePopover()
							}
						"
					>
						Done
					</Button>
				</div>
			</div>
		</template>
	</Popover>
</template>
