<script setup lang="ts">
import { inject } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { confirmDialog } from '../../helpers/confirm_dialog'
import { Query } from '../query'

const query = inject('query') as Query
function toggleLiveConnection(enable: boolean) {
	const title = enable ? 'Enable Cache' : 'Disable Cache'
	const message = enable
		? 'Enabling cache will make your queries faster by using stored data. However, this data may not be the most current, as it is updated once every 24 hours.'
		: 'Disabling cache will ensure you are always using the most up-to-date data, but your queries may take longer to complete.'

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
	<div class="flex flex-col px-2.5 py-2">
		<div class="mb-1 flex h-6 items-center justify-between">
			<div class="flex items-center gap-1">
				<div class="text-sm font-medium">Metadata</div>
			</div>
			<div></div>
		</div>
		<div class="flex flex-shrink-0 flex-col gap-2.5 px-0.5">
			<InlineFormControlLabel label="Query Title">
				<FormControl v-model="query.doc.title" autocomplete="off" placeholder="Title" />
			</InlineFormControlLabel>
			<InlineFormControlLabel label="Use Cache" class="!w-1/2">
				<Switch
					:modelValue="!query.doc.use_live_connection"
					@update:modelValue="toggleLiveConnection"
					:tabs="[
						{ label: 'Yes', value: true },
						{ label: 'No', value: false, default: true },
					]"
				/>
			</InlineFormControlLabel>
		</div>
	</div>
</template>
