<script setup lang="ts">
import { dayjs } from 'frappe-ui'
import { computed, inject } from 'vue'
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

const snapshotRefreshing = computed(
	() =>
		query.refreshingSnapshot ||
		query.doc.snapshot_status === 'Queued' ||
		query.doc.snapshot_status === 'Running',
)

const snapshotStatusLabel = computed(() => {
	if (snapshotRefreshing.value) return 'Refreshing…'
	if (query.doc.snapshot_status === 'Failed') return 'Last refresh failed'
	if (query.doc.snapshot_last_refreshed_at) {
		return `Updated ${dayjs(query.doc.snapshot_last_refreshed_at).fromNow()}`
	}
	return 'Not built yet'
})
</script>

<template>
	<div class="flex flex-col px-3.5 pt-3">
		<div class="mb-1 flex h-6 items-center justify-between">
			<div class="flex items-center gap-1">
				<div class="text-sm font-medium">Details</div>
			</div>
			<div></div>
		</div>
		<div class="flex flex-shrink-0 flex-col gap-3 border-b px-0.5 pb-3">
			<InlineFormControlLabel label="Query Title">
				<LazyTextInput type="text" placeholder="Title" v-model="query.doc.title" />
			</InlineFormControlLabel>
			<Toggle
				v-if="settings.doc.enable_data_store"
				label="Enable Data Store"
				:modelValue="!query.doc.use_live_connection"
				@update:modelValue="toggleLiveConnection"
			/>
			<Toggle
				label="Materialize Results"
				description="Store this query's result and serve it from the data store instead of re-running the query on every view. Best for heavy aggregated queries."
				v-model="query.doc.is_materialized"
			/>
			<template v-if="query.doc.is_materialized">
				<InlineFormControlLabel label="Refresh Frequency">
					<FormControl
						type="select"
						v-model="query.doc.snapshot_refresh_frequency"
						:options="['Daily', 'Hourly']"
					/>
				</InlineFormControlLabel>
				<div class="flex items-center justify-between">
					<div
						class="text-xs"
						:class="
							query.doc.snapshot_status === 'Failed'
								? 'text-ink-red-3'
								: 'text-ink-gray-5'
						"
						:title="query.doc.snapshot_error || ''"
					>
						{{ snapshotStatusLabel }}
					</div>
					<Button
						label="Refresh"
						icon-left="refresh-cw"
						:loading="snapshotRefreshing"
						@click="query.refreshSnapshot"
					/>
				</div>
			</template>
		</div>
	</div>
</template>
