<template>
	<div class="flex flex-1 flex-col space-y-4 overflow-hidden px-6 py-4">
		<div class="flex h-12 flex-shrink-0 items-center justify-between">
			<div class="text-3xl font-medium text-gray-900">Settings</div>
			<Button
				variant="primary "
				class="!rounded bg-gray-900 text-gray-50 shadow-sm hover:bg-gray-800"
				:disabled="updateDisabled"
				@click="settings.updateSettings(settingsDoc)"
			>
				Update
			</Button>
		</div>
		<div class="flex flex-1 flex-col space-y-6 overflow-scroll">
			<div class="rounded border bg-white p-6 shadow-sm">
				<div class="flex items-baseline">
					<div class="text-xl font-medium text-gray-700">General</div>
				</div>
				<div class="mt-4 flex flex-col space-y-8">
					<Setting
						label="Max Query Result Limit"
						description="Maximum number of rows to be returned by a query. This is to prevent long running queries and memory issues."
					>
						<Input type="number" min="0" v-model="settingsDoc.query_result_limit" />
						<div class="ml-2 text-gray-600">Rows</div>
					</Setting>

					<Setting
						label="Cache Query Results For"
						description="Number of minutes to cache query results. This is to prevent accidental running of the same query multiple times."
					>
						<Input type="number" min="0" v-model="settingsDoc.query_result_expiry" />
						<div class="ml-2 text-gray-600">Minutes</div>
					</Setting>

					<Setting
						label="Fiscal Year Start"
						description="Start of the fiscal year. This is used to calculate fiscal year for date columns."
					>
						<DatePicker
							placeholder="Select Date"
							:value="settingsDoc.fiscal_year_start"
							@change="settingsDoc.fiscal_year_start = $event"
						/>
					</Setting>

					<Setting
						label="Auto Execute Query"
						description="Automatically execute when tables, columns, or filters are changed."
					>
						<Input
							type="checkbox"
							v-model="settingsDoc.auto_execute_query"
							:label="settingsDoc.auto_execute_query ? 'Enabled' : 'Disabled'"
						/>
					</Setting>

					<Setting
						label="Enable Query Reusability"
						description="Allow selecting query as a table in another query. Any query selected as a table will be appended as a sub query using CTE (Common Table Expression)."
					>
						<Input
							type="checkbox"
							v-model="settingsDoc.allow_subquery"
							:label="settingsDoc.allow_subquery ? 'Enabled' : 'Disabled'"
						/>
					</Setting>
				</div>
			</div>

			<div v-if="settingsDoc.is_subscribed" class="rounded border bg-white p-6 shadow-sm">
				<div class="flex items-baseline">
					<div class="text-xl font-medium text-gray-700">Subscription</div>
				</div>
				<div class="mt-4 flex flex-col space-y-8">
					<Setting
						label="Support Login Link"
						description="Send a login link to the support portal. You can login to the support portal to manage support tickets."
					>
						<Button
							variant="outline"
							@click="settings.send_support_login_link.submit()"
							:loading="settings.send_support_login_link.loading"
							:disabled="
								!settingsDoc.is_subscribed ||
								settings.send_support_login_link.loading
							"
						>
							Send Login Link
						</Button>
					</Setting>
				</div>
			</div>
			<div class="rounded border bg-white p-6 shadow-sm">
				<div class="flex items-baseline">
					<div class="text-xl font-medium text-gray-700">Notifications</div>
				</div>
				<div class="mt-4 flex flex-col space-y-8">
					<Setting
						label="Telegram Bot Token"
						description="Telegram bot token to send notifications to Telegram."
					>
						<Input
							type="password"
							v-model="settingsDoc.telegram_api_token"
							placeholder="Telegram Bot Token"
						/>
					</Setting>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { updateDocumentTitle } from '@/utils'
import settings from '@/utils/settings'
import { computed, ref, watchEffect } from 'vue'
import Setting from '@/components/Setting.vue'
import DatePicker from '@/components/Controls/DatePicker.vue'

const settingsDoc = ref({})
watchEffect(() => {
	if (settings.doc) {
		settingsDoc.value = { ...settings.doc }
	} else {
		settingsDoc.value = {}
	}
})
const updateDisabled = computed(() => {
	const local = settingsDoc.value
	const remote = settings.doc
	if (!local || !remote) return true
	return (
		local.query_result_limit === remote.query_result_limit &&
		local.query_result_expiry === remote.query_result_expiry &&
		local.auto_execute_query === remote.auto_execute_query &&
		local.allow_subquery === remote.allow_subquery &&
		local.fiscal_year_start === remote.fiscal_year_start &&
		local.telegram_api_token === remote.telegram_api_token
	)
})

const pageMeta = ref({
	title: 'Settings',
})
updateDocumentTitle(pageMeta)
</script>
