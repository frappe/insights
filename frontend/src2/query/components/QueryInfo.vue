<script setup lang="ts">
import { inject } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { confirmDialog } from '../../helpers/confirm_dialog'
import { Query } from '../query'
import useSettings from '../../settings/settings'
import LazyTextInput from '../../components/LazyTextInput.vue'

const query = inject('query') as Query
const settings = useSettings()
function toggleLiveConnection(enable: boolean) {
	const title = enable ? 'Enable Data Store' : 'Disable Data Store'
	const message = enable
		? 'Enabling data store use the cached table data for faster queries, but may not be up-to-date. It will also allow you to combine data from multiple sources. Cached data is updated every day.'
		: 'Disabling data store will use the live connection to the database for queries. This will ensure that you are always querying the most up-to-date data but may be slower.'

	confirmDialog({
		title,
		message,
		onSuccess() {
			query.doc.use_live_connection = !enable
		},
	})
}
</script>

<template>
	<div class="flex flex-col px-3.5 pt-3">
		<div class="mb-1 flex h-6 items-center justify-between">
			<div class="flex items-center gap-1">
				<div class="text-sm font-medium">Details</div>
			</div>
			<div></div>
		</div>
		<div class="flex flex-shrink-0 flex-col gap-2.5 border-b px-0.5 pb-3">
			<InlineFormControlLabel label="Query Title">
				<LazyTextInput
					type="text"
					placeholder="Title"
					v-model="query.doc.title"
				/>
			</InlineFormControlLabel>
			<InlineFormControlLabel
				v-if="settings.doc.enable_data_store"
				label="Enable Data Store"
				class="!w-1/2"
			>
				<Toggle
					class="mt-1"
					:modelValue="!query.doc.use_live_connection"
					@update:modelValue="toggleLiveConnection"
				/>
			</InlineFormControlLabel>
		</div>
	</div>
</template>
