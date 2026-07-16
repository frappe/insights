<script setup lang="ts">
import { dayjs } from 'frappe-ui'
import { computed, inject } from 'vue'
import { __ } from '../../translation'
import { Query } from '../query'

const showDialog = defineModel()

const query = inject('query') as Query

const snapshotRefreshing = computed(
	() =>
		query.refreshingSnapshot ||
		query.doc.snapshot_status === 'Queued' ||
		query.doc.snapshot_status === 'Running',
)

const snapshotStatusLabel = computed(() => {
	if (snapshotRefreshing.value) return __('Refreshing…')
	if (query.doc.snapshot_status === 'Failed') return __('Last refresh failed')
	if (query.doc.snapshot_last_refreshed_at) {
		return __('Updated {0}', dayjs(query.doc.snapshot_last_refreshed_at).fromNow())
	}
	return __('Not built yet')
})
</script>

<template>
	<Dialog
		v-model="showDialog"
		:options="{ title: __('Materialization'), size: 'lg' }"
		:dismissable="true"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<Toggle
					:label="__('Materialize Results')"
					:description="
						__(
							`Store this query's result and serve it from the data store instead of re-running the query on every view. Best for heavy aggregated queries.`,
						)
					"
					v-model="query.doc.is_materialized"
				/>

				<template v-if="query.doc.is_materialized">
					<FormControl
						type="select"
						:label="__('Refresh Frequency')"
						v-model="query.doc.snapshot_refresh_frequency"
						:options="['Daily', 'Hourly']"
					/>

					<div class="flex items-center justify-between border-t pt-3">
						<div
							class="text-sm"
							:class="
								query.doc.snapshot_status === 'Failed'
									? 'text-ink-red-3'
									: 'text-ink-gray-6'
							"
							:title="query.doc.snapshot_error || ''"
						>
							{{ snapshotStatusLabel }}
						</div>
						<Button
							:label="__('Refresh Now')"
							icon-left="refresh-cw"
							:loading="snapshotRefreshing"
							@click="query.refreshSnapshot"
						/>
					</div>
				</template>
			</div>
		</template>
	</Dialog>
</template>
