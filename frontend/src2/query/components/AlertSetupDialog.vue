<script setup lang="tsx">
import { Textarea } from 'frappe-ui'
import { computed, reactive, unref } from 'vue'
import Checkbox from '../../components/Checkbox.vue'
import { waitUntil, wheneverChanges } from '../../helpers'
import { createToast } from '../../helpers/toasts'
import useAlertStore from '../alert'
import { Query } from '../query'
import ExpressionEditor from './ExpressionEditor.vue'

const props = defineProps<{ query: Query; alert_name: string }>()
const show = defineModel()

const alert = useAlertStore().getAlert(props.alert_name)

const filterCondition = reactive({
	left: '',
	operator: '==',
	right: '',
})

waitUntil(() => alert.isloaded).then(() => {
	if (alert.doc.condition) {
		const regex = /q\['(.*)'\] ([!=><]+) (.*)/
		const match = alert.doc.condition.match(regex)
		if (match) {
			filterCondition.left = match[1]
			filterCondition.operator = match[2]
			filterCondition.right = match[3]
		}
	}
})

wheneverChanges(
	() => filterCondition,
	() => {
		alert.doc.custom_condition = 0
		alert.doc.condition = `q['${filterCondition.left}'] ${filterCondition.operator} ${filterCondition.right}`
	},
	{ deep: true }
)

const isValidAlert = computed(() => {
	if (!alert.doc.title) return false
	if (!alert.doc.frequency) return false
	if (alert.doc.frequency === 'Cron' && !alert.doc.cron_format) return false
	if (!alert.doc.channel) return false
	if (alert.doc.channel === 'Email' && !alert.doc.recipients) return false
	if (alert.doc.channel === 'Telegram' && !alert.doc.telegram_chat_id) return false
	if (alert.doc.custom_condition && !alert.doc.condition) return false
	if (!alert.doc.custom_condition && !filterCondition.left) return false
	if (!alert.doc.custom_condition && !filterCondition.operator) return false
	if (!alert.doc.custom_condition && !filterCondition.right) return false
	if (!alert.doc.message) return false
	return true
})

function updateAlert() {
	if (!alert.isdirty) return
	if (!isValidAlert.value) return

	const isNew = unref(alert.islocal)
	if (isNew) {
		alert.doc.query = props.query.doc.name
	}
	alert.doc.disabled = 0
	return alert.save().then(() => {
		createToast({
			title: isNew ? 'Alert Created' : 'Alert Updated',
			message: `Alert "${alert.doc.title}" has been ${isNew ? 'created' : 'updated'}.`,
			variant: 'success',
		})
		show.value = false
	})
}

function testSendAlert() {
	if (!isValidAlert.value) return
	if (alert.islocal) {
		alert.doc.query = props.query.doc.name
	}
	return alert.call('test_alert').then(() => {
		createToast({
			title: 'Alert Sent',
			message: `Alert "${alert.doc.title}" has been sent.`,
			variant: 'success',
		})
	})
}

function toggleAlert() {
	alert.doc.disabled = alert.doc.disabled ? 0 : 1
	return alert.save().then(() => {
		createToast({
			title: alert.doc.disabled ? 'Alert Disabled' : 'Alert Enabled',
			message: `Alert "${alert.doc.title}" has been ${
				alert.doc.disabled ? 'disabled' : 'enabled'
			}.`,
			variant: 'success',
		})
	})
}
</script>

<template>
	<Dialog
		v-model="show"
		:disableOutsideClickToClose="alert.isdirty || alert.islocal"
		:options="{
			title: 'Setup Alert',
			size: '2xl',
			actions: [
				{
					label: 'Send Test Alert',
					disabled: !isValidAlert || alert.loading || alert.saving,
					loading: alert.loading,
					onClick: testSendAlert,
				},
				{
					label: alert.doc.disabled ? 'Enable Alert' : 'Disable Alert',
					disabled: alert.loading || alert.saving,
					loading: alert.loading,
					onClick: toggleAlert,
				},
				{
					label: alert.islocal ? 'Create Alert' : 'Update Alert',
					variant: 'solid',
					disabled: !isValidAlert || !alert.isdirty || alert.saving || alert.loading,
					loading: alert.saving,
					onClick: updateAlert,
				},
			],
		}"
	>
		<template #body-content>
			<div class="flex flex-col gap-3 text-base">
				<div class="flex gap-4">
					<div class="flex flex-1 flex-col gap-3">
						<FormControl
							type="text"
							label="Alert Name"
							v-model="alert.doc.title"
							placeholder="e.g. Low Inventory"
						/>
						<FormControl
							type="select"
							label="Frequency"
							v-model="alert.doc.frequency"
							:options="[
								{ value: 'Hourly', label: 'Check once an hour' },
								{ value: 'Daily', label: 'Check once a day' },
								{ value: 'Weekly', label: 'Check once a week' },
								{ value: 'Monthly', label: 'Check once a month' },
								{ value: 'Cron', label: 'Cron' },
							]"
						/>
						<FormControl
							v-if="alert.doc.frequency === 'Cron'"
							type="text"
							label="Cron"
							v-model="alert.doc.cron_format"
							placeholder="e.g. 0 0 12 * * ?"
						/>
					</div>
					<div class="flex flex-1 flex-col gap-3">
						<FormControl
							type="select"
							label="Channel"
							v-model="alert.doc.channel"
							:options="[
								{ label: 'Email', value: 'Email' },
								// { label: 'Telegram', value: 'Telegram' },
							]"
						/>
						<FormControl
							v-if="alert.doc.channel === 'Email'"
							type="text"
							label="Recipients"
							v-model="alert.doc.recipients"
							placeholder="e.g. john@example.com, henry@example.com"
						/>
						<FormControl
							v-if="alert.doc.channel === 'Telegram'"
							type="text"
							label="Telegram Chat ID"
							v-model="alert.doc.telegram_chat_id"
							placeholder="e.g. 123456789"
						/>
					</div>
				</div>

				<div class="flex flex-col">
					<label class="mb-1.5 block text-xs text-ink-gray-5">Send alert when</label>
					<div class="flex gap-4" v-if="!alert.doc.custom_condition">
						<FormControl
							type="select"
							class="flex-1"
							placeholder="Select Field"
							v-model="filterCondition.left"
							:options="props.query.result.columnOptions"
						/>
						<FormControl
							type="select"
							class="flex-1"
							v-model="filterCondition.operator"
							:options="['==', '!=', '>', '>=', '<', '<=']"
						/>
						<FormControl
							type="text"
							class="flex-1"
							v-model="filterCondition.right"
							placeholder="e.g. 100"
						/>
					</div>
					<div v-else>
						<ExpressionEditor
							language="python"
							placeholder="e.g. order_count < 100"
							class="inline-expression h-fit max-h-[10rem] min-h-[5rem] text-sm"
							v-model="alert.doc.condition"
							:column-options="props.query.result.columnOptions"
						/>
					</div>
					<Checkbox
						class="mt-1.5"
						label="Use Custom Condition"
						v-model="alert.doc.custom_condition"
					/>
				</div>

				<div>
					<Textarea
						label="Message"
						class="min-h-40 text-p-sm"
						v-model="alert.doc.message"
						:placeholder="`e.g.
Hey,
We have **low inventory** for **{{ title }}**.
Please order more.
Thanks,
						`"
					/>

					<div class="mt-2 text-p-sm text-gray-600">
						You can use markdown to format the message. Use double asterisks (**) for
						bold text. You can use the following fields in the message:

						<div
							v-html="
								`<ul class='list-disc pl-4'>
							<li>{{ rows }} - The result of the query</li>
							<li>{{ count }} - The number of rows in the query</li>
						</ul>`
							"
						/>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
