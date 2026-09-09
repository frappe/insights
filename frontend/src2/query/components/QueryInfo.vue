<script setup lang="ts">
import { Database, DatabaseZap, User } from 'lucide-vue-next'
import { computed, inject, type Component } from 'vue'
import { getDataSourceList } from '../../data_source/data_source'
import { confirmDialog } from '../../helpers/confirm_dialog'
import useSettings from '../../settings/settings'
import { __ } from '../../translation'
import useUserStore from '../../users/users'
import { Query } from '../query'

const query = inject('query') as Query
const settings = useSettings()
const users = useUserStore()

const sources = getDataSourceList()
const sourceTitle = (name: string) => sources.value.find((s) => s.name === name)?.title || name

// Every source the pipeline reads, not only the first step's: a join or a
// union may bring a second one in, which is what the data store is for.
const sourceNames = computed(() => {
	const names = new Set<string>()
	for (const op of query.doc.operations) {
		if (op.type === 'sql') names.add(op.data_source)
		if (op.type === 'source' || op.type === 'join' || op.type === 'union') {
			if (op.table.type === 'table') names.add(op.table.data_source)
		}
	}
	if (!names.size && query.dataSource) names.add(query.dataSource)
	return [...names].filter(Boolean)
})

const details = computed(() => {
	const rows: { label: string; value: string; icon: Component }[] = []
	if (sourceNames.value.length) {
		rows.push({
			icon: Database,
			label: sourceNames.value.length > 1 ? __('Sources') : __('Source'),
			value: sourceNames.value.map(sourceTitle).join(', '),
		})
	}
	if (query.doc.owner)
		rows.push({
			icon: User,
			label: __('Owner'),
			value: users.getName(query.doc.owner) || query.doc.owner,
		})
	return rows
})

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
	<div class="flex flex-col px-3.5 pt-3.5">
		<div class="mb-1 flex h-6 items-center justify-between">
			<div class="flex items-center gap-1">
				<div class="text-sm-medium">Details</div>
			</div>
			<div></div>
		</div>
		<div class="flex flex-shrink-0 flex-col border-b px-0.5 pb-3">
			<div
				v-for="row in details"
				:key="row.label"
				class="flex h-7 items-center justify-between gap-3 text-sm"
			>
				<span class="flex items-center gap-2 text-ink-gray-5">
					<component :is="row.icon" class="size-3.5 text-ink-gray-5" stroke-width="1.5" />
					{{ row.label }}
				</span>
				<span class="truncate text-ink-gray-8" :title="row.value">
					{{ row.value }}
				</span>
			</div>
			<div
				v-if="settings.doc.enable_data_store"
				class="flex h-7 items-center justify-between gap-3 text-sm"
			>
				<span class="flex items-center gap-2 text-ink-gray-5">
					<DatabaseZap class="size-3.5 text-ink-gray-5" stroke-width="1.5" />
					{{ __('Data store') }}
				</span>
				<Toggle
					:modelValue="!query.doc.use_live_connection"
					@update:modelValue="toggleLiveConnection"
				/>
			</div>
		</div>
	</div>
</template>
