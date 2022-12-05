<script setup>
import { Dialog } from 'frappe-ui'
import DashboardFilterForm from './DashboardFilterForm.vue'
import Autocomplete from '@/components/Controls/Autocomplete.vue'
import TimespanPicker from '@/components/Controls/TimespanPicker.vue'
import ListPicker from '@/components/Controls/ListPicker.vue'
import DatePicker from '@/components/Controls/DatePicker.vue'
import DateRangePicker from '@/components/Controls/DateRangePicker.vue'

import { computed, reactive, watch, inject, ref } from 'vue'
import { formatDate } from '@/utils'

const dashboard = inject('dashboard')
const props = defineProps({ item: Object })

const filter = reactive({
	filter_label: props.item.filter_label,
	filter_type: props.item.filter_type,
	filter_operator: props.item.filter_operator,
	filter_value: props.item.filter_value,
	filter_links: props.item.filter_links,
})

watch(
	() => filter.filter_value,
	() => {
		dashboard.update_filter
			.submit({
				filter: {
					name: props.item.name,
					...filter,
				},
			})
			.then(dashboard.refreshItems)
			.catch((e) => {
				console.error(e)
			})
	}
)

const showEditFilterDialog = ref(false)
function editFilter() {
	dashboard.update_filter
		.submit({
			filter: {
				name: props.item.name,
				...filter,
			},
		})
		.then(dashboard.refreshItems)
		.catch((e) => {
			console.error(e)
		})
	showEditFilterDialog.value = false
}

const valueType = computed(() => {
	if (
		['Date', 'Datetime'].includes(filter.filter_type) &&
		['=', '!=', '>', '>=', '<', '<=', 'between'].includes(filter.filter_operator)
	) {
		return 'datePicker'
	}

	if (
		['Date', 'Datetime'].includes(filter.filter_type) &&
		filter.filter_operator === 'timespan'
	) {
		return 'timespanPicker'
	}
})
</script>

<template>
	<div class="h-full w-full rounded-md border px-3 py-2">
		<div class="mb-2 flex items-center justify-between">
			<div class="text-gray-600">{{ filter.filter_label }}</div>
			<teleport :to="`#dashboard-item-actions-${item.name}`">
				<div
					v-if="dashboard.editingLayout"
					class="cursor-pointer rounded p-1 text-gray-600 hover:bg-gray-100"
				>
					<FeatherIcon
						name="settings"
						class="h-4 w-4"
						@mousedown.prevent.stop=""
						@click="showEditFilterDialog = true"
					/>
				</div>
			</teleport>
		</div>

		<DateRangePicker
			v-if="valueType == 'datePicker' && filter.filter_operator == 'between'"
			id="value"
			:value="filter.filter_value"
			:formatter="formatDate"
			placeholder="Select Date"
			@change="(date) => (filter.filter_value = date)"
		/>
		<DatePicker
			v-else-if="valueType == 'datePicker'"
			id="value"
			:value="filter.filter_value"
			placeholder="Select Date"
			:formatter="formatDate"
			@change="(date) => (filter.filter_value = date)"
		/>
		<TimespanPicker
			v-else-if="valueType == 'timespanPicker'"
			id="value"
			:value="filter.filter_value"
			placeholder="Select Timespan"
			@change="(timespan) => (filter.filter_value = timespan)"
		/>
		<Input v-else type="text" class="h-8" v-model="filter.filter_value"></Input>
	</div>

	<Dialog :options="{ title: 'Edit Filter' }" v-model="showEditFilterDialog" :dismissable="true">
		<template #body-content>
			<DashboardFilterForm v-model="filter" />
		</template>
		<template #actions>
			<Button appearance="primary" @click="editFilter"> Done </Button>
		</template>
	</Dialog>
</template>
