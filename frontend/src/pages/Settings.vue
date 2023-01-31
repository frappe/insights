<template>
	<div class="flex flex-1 flex-col space-y-4 overflow-hidden px-6 py-4">
		<div class="flex h-12 flex-shrink-0 items-center justify-between">
			<div class="text-3xl font-medium text-gray-900">Settings</div>
			<Button
				:appearance="updateDisabled ? 'white' : 'primary'"
				class="shadow-sm"
				:disabled="updateDisabled"
				@click="settings.updateSettings(settingsDoc)"
			>
				Update
			</Button>
		</div>
		<div class="flex flex-1 flex-col space-y-6 overflow-scroll">
			<div class="rounded-lg border bg-white p-6 shadow-sm">
				<div class="flex items-baseline">
					<div class="text-xl font-medium text-gray-700">General</div>
				</div>
				<div class="mt-4 flex flex-col space-y-8">
					<div class="flex">
						<div class="flex-1">
							<p class="font-medium leading-6 text-gray-900">
								Max Query Result Limit
							</p>
							<span class="text-gray-500">
								Maximum number of rows to be returned by a query. This is to prevent
								accidental queries from returning too many rows.
							</span>
						</div>
						<div class="flex flex-1 items-center pl-20">
							<Input type="number" min="0" v-model="settingsDoc.query_result_limit" />
							<div class="ml-2 text-gray-500">Rows</div>
						</div>
					</div>

					<div class="flex">
						<div class="flex-1">
							<p class="font-medium leading-6 text-gray-900">
								Cache Query Results For
							</p>
							<span class="text-gray-500">
								Number of minutes to cache query results. This is to prevent
								accidental queries from running too many times.
							</span>
						</div>
						<div class="flex flex-1 items-center pl-20">
							<Input
								type="number"
								min="0"
								v-model="settingsDoc.query_result_expiry"
							/>
							<div class="ml-2 text-gray-500">Minutes</div>
						</div>
					</div>

					<div class="flex">
						<div class="flex-1">
							<p class="font-medium leading-6 text-gray-900">Auto Execute Query</p>
							<span class="text-gray-500">
								Automatically execute when tables, columns, or filters are changed.
							</span>
						</div>
						<div class="flex flex-1 items-center pl-20">
							<Input
								type="checkbox"
								v-model="settingsDoc.auto_execute_query"
								:label="settingsDoc.auto_execute_query ? 'Enabled' : 'Disabled'"
							/>
						</div>
					</div>
				</div>
			</div>

			<div class="rounded-lg border bg-white p-6 shadow-sm">
				<div class="flex items-baseline">
					<div class="text-xl font-medium text-gray-700">Subscription</div>
				</div>
				<div class="mt-4 flex flex-col space-y-8">
					<div class="flex">
						<div class="flex-1">
							<p class="font-medium leading-6 text-gray-900">Subscription ID</p>
							<span class="text-gray-500">
								This is used for authentication with the support portal and managing
								support tickets.
							</span>
						</div>
						<div class="flex flex-1 items-center pl-20">
							<Input
								type="password"
								v-model="settingsDoc.subscription_id"
								placeholder="eg. 1234567890"
							/>
						</div>
					</div>

					<div class="flex">
						<div class="flex-1">
							<p class="font-medium leading-6 text-gray-900">Support Login</p>
							<span class="text-gray-500">
								Send a login link to the support portal. You can login to the
								support portal to manage support tickets.
							</span>
						</div>
						<div class="flex flex-1 items-center pl-20">
							<Button
								appearance="white"
								@click="settings.send_support_login_link.submit()"
								:loading="settings.send_support_login_link.loading"
								:disabled="
									!settingsDoc.subscription_id ||
									settings.send_support_login_link.loading
								"
							>
								Send Login Link
							</Button>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script setup>
import { updateDocumentTitle } from '@/utils'
import settings from '@/utils/settings'
import { computed, ref, watchEffect } from 'vue'

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
		local.subscription_id === remote.subscription_id
	)
})

const pageMeta = ref({
	title: 'Settings',
})
updateDocumentTitle(pageMeta)
</script>
