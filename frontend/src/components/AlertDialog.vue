<script setup>
import Code from '@/components/Controls/Code.vue'
import { useQuery } from '@/utils/query'
import { createResource } from 'frappe-ui'
import { computed, reactive } from 'vue'

const emit = defineEmits(['update:show'])
const props = defineProps({
	show: Boolean,
	queryName: String,
})

const show = computed({
	get: () => props.show,
	set: (value) => {
		emit('update:show', value)
	},
})

const query = useQuery(props.queryName)
const alert = reactive({
	title: '',
	query: props.queryName,
	frequency: 'Daily',
	cron: null,
	channel: 'Email',
	recipients: '',
	telegram_chat_id: null,
	condition: {
		isAdvanced: false,
		left: query.results?.allColumnOptions[0],
		operator: '=',
		right: null,
		advanceCondition: null,
	},
})

const frequencyOptions = [
	{ label: 'Daily', value: 'Daily' },
	{ label: 'Weekly', value: 'Weekly' },
	{ label: 'Monthly', value: 'Monthly' },
	{ label: 'Custom', value: 'Custom' },
]
const channelOptions = [
	{ label: 'Email', value: 'Email' },
	{ label: 'Telegram', value: 'Telegram' },
]
const operatorOptions = ['=', '!=', '>', '>=', '<', '<=']
const createAlertDisabled = computed(() => {
	if (!alert.title) return true
	if (!alert.frequency) return true
	if (alert.frequency === 'Custom' && !alert.cron) return true
	if (!alert.channel) return true
	if (alert.channel === 'Email' && !alert.recipients) return true
	if (alert.channel === 'Telegram' && !alert.telegram_chat_id) return true
	if (alert.condition.isAdvanced && !alert.condition.advanceCondition) return true
	if (!alert.condition.left) return true
	if (!alert.condition.operator) return true
	if (!alert.condition.right) return true
	return false
})
const createAlertResource = createResource({ url: 'insights.api.create_alert' })
function makeCondition() {
	return alert.condition.isAdvanced
		? alert.condition.advanceCondition
		: `result['${alert.condition.left}'][0] ${alert.condition.operator} ${alert.condition.right}`
}
function createAlert() {
	if (createAlertDisabled.value) return
	const _alert = { ...alert }
	_alert.condition = makeCondition()
	createAlertResource
		.submit({
			alert: _alert,
		})
		.then((res) => {
			console.log(res)
			show.value = false
		})
}
const testAlertResource = createResource({ url: 'insights.api.test_alert' })
function testSendAlert() {
	if (createAlertDisabled.value) return
	const _alert = { ...alert }
	_alert.condition = makeCondition()
	testAlertResource
		.submit({
			alert: _alert,
		})
		.then((res) => {
			console.log(res)
		})
}
</script>

<template>
	<Dialog :options="{ title: 'Create Alert' }" v-model="show" :dismissable="true">
		<template #body-content>
			<div class="space-y-4 text-base">
				<Input
					type="text"
					label="Alert Name"
					v-model="alert.title"
					placeholder="e.g. Low Inventory"
				/>
				<Input
					type="select"
					label="Frequency"
					v-model="alert.frequency"
					:options="frequencyOptions"
				/>
				<Input
					v-if="alert.frequency === 'Custom'"
					type="text"
					label="Cron"
					v-model="alert.cron"
					placeholder="e.g. 0 0 12 * * ?"
				/>
				<Input
					type="select"
					label="Channel"
					v-model="alert.channel"
					:options="channelOptions"
				/>
				<Input
					v-if="alert.channel === 'Email'"
					type="text"
					label="Recipients"
					v-model="alert.recipients"
					placeholder="e.g. john@example.com, henry@example.com"
				/>
				<Input
					v-if="alert.channel === 'Telegram'"
					type="text"
					label="Telegram Chat ID"
					v-model="alert.telegram_chat_id"
					placeholder="e.g. 123456789"
				/>
				<p class="text-lg font-medium text-gray-800">Send alert when</p>
				<div class="flex gap-4" v-if="!alert.condition.isAdvanced">
					<Input
						type="select"
						class="flex-2"
						v-model="alert.condition.left"
						:options="query.results.allColumnOptions"
					/>
					<Input
						type="select"
						class="flex-1"
						v-model="alert.condition.operator"
						:options="operatorOptions"
					/>
					<Input
						type="text"
						class="flex-2"
						v-model="alert.condition.right"
						placeholder="e.g. 100"
					/>
				</div>
				<div v-else>
					<Code v-model="alert.condition.advanceCondition" />
				</div>
				<Input
					type="checkbox"
					label="Use Advanced Condition"
					v-model="alert.condition.isAdvanced"
				/>
			</div>
		</template>
		<template #actions>
			<Button
				appearance="primary"
				:disabled="createAlertDisabled"
				:loading="createAlertResource.loading"
				@click="createAlert"
			>
				Create
			</Button>
			<Button
				:disabled="createAlertDisabled"
				:loading="testSendAlert.loading"
				@click="testSendAlert"
			>
				Test
			</Button>
		</template>
	</Dialog>
</template>
