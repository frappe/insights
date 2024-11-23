<script setup lang="ts">
import { inject } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { confirmDialog } from '../../helpers/confirm_dialog'
import { Query } from '../query'

const query = inject('query') as Query
function toggleLiveConnection(enable: boolean) {
	const title = enable ? 'Enable Data Store' : 'Disable Data Store'
	const message = enable
		? 'Enabling the data store will make your queries faster by using stored data. However, this data may not be the most current, as it is updated once every 24 hours.'
		: 'Disabling the data store will ensure you are always using the most up-to-date data, but your queries may take longer to run.'

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
				<FormControl v-model="query.doc.title" autocomplete="off" placeholder="Title" />
			</InlineFormControlLabel>
			<InlineFormControlLabel label="Enable Data Store" class="!w-1/2">
				<Checkbox
					class="mt-1"
					:modelValue="!query.doc.use_live_connection"
					@update:modelValue="toggleLiveConnection"
				/>
			</InlineFormControlLabel>
		</div>
	</div>
</template>
