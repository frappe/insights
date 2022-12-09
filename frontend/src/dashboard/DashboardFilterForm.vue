<script setup>
import { computed, reactive, inject } from 'vue'
import { getOperatorOptions } from '@/utils/query/columns'

const props = defineProps({ modelValue: Object })
const emits = defineEmits(['update:modelValue'])

const filter = computed({
	get: () => props.modelValue,
	set: (value) => emits('update:modelValue', value),
})

const filterTypeOptions = ['String', 'Integer', 'Decimal', 'Date', 'Datetime']
const operatorOptions = computed(() => getOperatorOptions(filter.value.filter_type))

const dashboard = inject('dashboard')
const chartItems = computed(() => dashboard.items.filter((item) => item.item_type === 'Chart'))

function handleCheck(checked, chartItem) {
	const filter_links = filter.value.filter_links || {}
	if (checked) {
		filter_links[chartItem.chart] = {}
		if (!columnOptions[chartItem.query]) {
			setColumnOptions(chartItem)
		}
	} else {
		delete filter_links[chartItem.chart]
	}
	filter.value = { ...filter.value, filter_links }
}

const columnOptions = reactive({})
function setColumnOptions(chartItem) {
	const request = dashboard.fetchAllColumns(chartItem.query)
	columnOptions[chartItem.chart] = computed(() => {
		return request.data
			?.filter((c) => c.type === filter.value.filter_type)
			.map((column) => {
				return {
					label: column.label,
					column: column.column,
					table: column.table,
					type: column.type,
					table_label: column.table_label,
					value: `${column.table}.${column.column}`,
				}
			})
	})
}
</script>

<template>
	<div class="space-y-3">
		<Input type="text" label="Label" v-model="filter.filter_label"></Input>
		<Input
			type="select"
			label="Type"
			v-model="filter.filter_type"
			:options="filterTypeOptions"
		></Input>
		<Input
			type="select"
			label="Operator"
			:options="operatorOptions"
			v-model="filter.filter_operator"
		></Input>
		<div>
			<div class="mb-2 block text-sm leading-4 text-gray-700">Links</div>
			<div class="max-h-[15rem] space-y-2 overflow-y-auto">
				<div
					class="flex h-8 w-full items-center text-gray-600"
					v-for="chartItem in chartItems"
					:key="chartItem.chart"
				>
					<div
						class="flex flex-1 items-center text-ellipsis whitespace-nowrap text-base font-medium"
					>
						<Input
							type="checkbox"
							:label="chartItem.chart_title"
							class="focus:ring-0"
							@change="handleCheck($event, chartItem)"
							:value="filter.filter_links[chartItem.chart]"
						></Input>
					</div>
					<Autocomplete
						v-if="filter.filter_links[chartItem.chart]"
						placeholder="Select Column"
						:options="columnOptions[chartItem.chart]"
						v-model="filter.filter_links[chartItem.chart]"
						:empty-text="`No ${filter.filter_type} columns found`"
					></Autocomplete>
				</div>
			</div>
		</div>
	</div>
</template>
