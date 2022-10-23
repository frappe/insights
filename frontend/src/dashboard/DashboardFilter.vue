<script setup>
import { Dialog } from 'frappe-ui'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import TimespanPicker from '@/components/Controls/TimespanPicker.vue'
import ListPicker from '@/components/Controls/ListPicker.vue'
import DatePicker from '@/components/Controls/DatePicker.vue'

import { computed, reactive, watch, inject, ref } from 'vue'
import { getOperatorOptions } from '@/utils/query/columns'
import { formatDate } from '@/utils'

const dashboard = inject('dashboard')
const props = defineProps({ item: Object })

const filter = reactive({
	label: props.item.filter_label,
	type: props.item.filter_type,
	operator: props.item.filter_operator,
	value: props.item.filter_value,
})

const filterTypeOptions = ['String', 'Integer', 'Decimal', 'Date', 'Datetime']
const operatorOptions = computed(() => getOperatorOptions(props.item.filter_type))

watch(
	() => filter,
	() => {
		dashboard.update_filter
			.submit({
				filter: {
					name: props.item.name,
					...filter,
				},
			})
			.then(() => {
				dashboard.refreshItems()
			})
	},
	{ deep: true }
)

const showEditFilterDialog = ref(false)

const valueType = computed(() => {
	if (
		['Date', 'Datetime'].includes(filter.type) &&
		['=', '!=', '>', '>=', '<', '<='].includes(filter.operator)
	) {
		return 'datePicker'
	}

	if (['Date', 'Datetime'].includes(filter.type) && filter.operator === 'timespan') {
		return 'timespanPicker'
	}
})
</script>

<template>
	<div class="h-full w-full rounded-md border px-3 py-2">
		<div class="flex items-center justify-between">
			<div class="mb-2 text-gray-600">{{ filter.label }}</div>
			<div
				class="mb-2 cursor-pointer text-sm text-gray-600 hover:underline"
				@click="showEditFilterDialog = true"
			>
				Edit
			</div>
		</div>

		<DatePicker
			v-if="valueType == 'datePicker'"
			id="value"
			:value="filter.value"
			placeholder="Select Date"
			:formatValue="formatDate"
			@change="(date) => (filter.value = date)"
		/>
		<TimespanPicker
			v-else-if="valueType == 'timespanPicker'"
			id="value"
			:value="filter.value"
			placeholder="Select Timespan"
			@change="(timespan) => (filter.value = timespan)"
		/>
		<Input v-else type="text" class="h-8" v-model="filter.value"></Input>
	</div>

	<Dialog :options="{ title: 'Edit Filter' }" v-model="showEditFilterDialog" :dismissable="true">
		<template #body-content>
			<div class="space-y-3">
				<Input type="text" label="Label" v-model="filter.label"></Input>
				<Input
					type="select"
					label="Type"
					v-model="filter.type"
					:options="filterTypeOptions"
				></Input>
				<Input
					type="select"
					label="Operator"
					:options="operatorOptions"
					v-model="filter.operator"
				></Input>
			</div>
		</template>
		<template #actions>
			<Button appearance="primary" @click="showEditFilterDialog = false"> Done </Button>
		</template>
	</Dialog>
</template>
