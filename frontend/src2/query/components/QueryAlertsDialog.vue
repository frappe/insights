<script setup lang="tsx">
import { useTimeAgo } from '@vueuse/core'
import { ListView } from 'frappe-ui'
import { Plus, SearchIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import IndicatorIcon from '../../components/Icons/IndicatorIcon.vue'
import { getUniqueId } from '../../helpers'
import useAlertStore from '../alert'
import { Query } from '../query'

const emit = defineEmits({
	'set-current-alert-name': (alert_name: string) => true,
})
const props = defineProps<{ query: Query }>()

const show = defineModel()

const alertStore = useAlertStore()
alertStore.loadAlerts(props.query.doc.name)

const searchQuery = ref('')
const filteredAlerts = computed(() => {
	if (!searchQuery.value) {
		return alertStore.alerts
	}
	return alertStore.alerts.filter(
		(alert: any) =>
			alert.title.toLowerCase().includes(searchQuery.value.toLowerCase()) ||
			alert.owner.toLowerCase().includes(searchQuery.value.toLowerCase())
	)
})

const listOptions = ref({
	columns: [
		{
			label: 'Title',
			key: 'title',
		},
		{
			label: 'Status',
			key: 'disabled',
			getLabel: (props: any) => {
				return props.row.disabled ? 'Disabled' : 'Enabled'
			},
			prefix: (props: any) => {
				const color = props.row.disabled ? 'text-gray-500' : 'text-green-500'
				return <IndicatorIcon class={color} />
			},
		},
		{
			label: 'Created By',
			key: 'owner',
		},
		{
			label: 'Last Execution',
			key: 'last_execution',
			getLabel: (props: any) => {
				if (!props.row.last_execution) {
					return ''
				}
				return useTimeAgo(props.row.last_execution).value
			},
		},
	],
	rows: filteredAlerts,
	rowKey: 'name',
	options: {
		selectable: true,
		showTooltip: false,
		onRowClick: (alert: any) => {
			emit('set-current-alert-name', alert.name)
			show.value = false
		},
		emptyState: {
			title: 'No alerts',
			description: 'Set up alerts to get notified when a condition is met',
			button: {
				label: 'New Alert',
				variant: 'solid',
				onClick: () => {
					emit('set-current-alert-name', 'new-alert-' + getUniqueId())
					show.value = false
				},
			},
		},
	},
})
</script>

<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Alerts',
			size: '2xl',
		}"
	>
		<template #body-content>
			<div class="flex h-[30rem] w-full flex-1 flex-col gap-3 overflow-auto text-base">
				<div class="flex justify-between gap-2 overflow-visible py-1">
					<FormControl placeholder="Search" v-model="searchQuery" :debounce="300">
						<template #prefix>
							<SearchIcon class="h-4 w-4 text-gray-500" />
						</template>
					</FormControl>
					<Button
						label="New Alert"
						variant="outline"
						@click="
							() => {
								emit('set-current-alert-name', 'new-alert-' + getUniqueId())
								show = false
							}
						"
					>
						<template #prefix>
							<Plus class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
				</div>
				<ListView class="h-full" v-bind="listOptions"> </ListView>
			</div>
		</template>
	</Dialog>
</template>
