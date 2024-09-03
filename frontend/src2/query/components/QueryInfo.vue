<script setup lang="ts">
import { inject } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { Query } from '../query'

const query = inject('query') as Query
window.toggleLiveConnection = () => {
	query.doc.use_live_connection = !query.doc.use_live_connection
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
		</div>
	</div>
</template>
