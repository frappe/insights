<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import {
	Copy,
	CopyPlus,
	MoreHorizontal,
	PlayIcon,
	RefreshCw,
	Scroll,
	ScanSearch,
} from 'lucide-vue-next'
import { computed, h, inject, ref } from 'vue'
import { Query } from '../query'
import { __ } from '../../translation'
import ExplainPlanDialog from './ExplainPlanDialog.vue'
import ViewSQLDialog from './ViewSQLDialog.vue'
import session from '../../session'

const query = inject('query') as Query

const showViewSQLDialog = ref(false)
const showExplainDialog = ref(false)

async function openExplainDialog() {
	showExplainDialog.value = true
	await query.explainQuery()
}

const moreActions = computed(() => {
	const actions = []

	if (!query.doc.use_live_connection && session.user.is_admin) {
		actions.push({
			label: __('Refresh Stored Tables'),
			icon: h(RefreshCw, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
			onClick: query.refreshStoredTables,
		})
	}

	actions.push(
		{
			label: __('View SQL'),
			icon: h(Scroll, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
			onClick: () => (showViewSQLDialog.value = true),
		},
		{
			label: __('Duplicate Query'),
			icon: h(CopyPlus, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
			onClick: () => query.duplicate(),
		},
		{
			label: __('Copy Query'),
			icon: h(Copy, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
			onClick: () => query.copy(),
		},
	)

	if (session.user.is_admin) {
		actions.push({
			label: __('Explain Plan'),
			icon: h(ScanSearch, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
			onClick: openExplainDialog,
		})
	}

	return actions
})
</script>

<template>
	<div class="flex w-full flex-shrink-0 items-center justify-between bg-white">
		<div>
			<div
				v-show="query.result.executedSQL"
				class="tnum flex items-center gap-2 text-sm text-gray-600"
			>
				<div class="h-2 w-2 rounded-full bg-green-500"></div>
				<div class="flex items-center gap-1">
					<span v-if="query.result.timeTaken == -1">
						{{ __('Fetched from cache') }}
					</span>
					<span v-else>
						{{ __('Fetched in {0}s', String(query.result.timeTaken)) }}
					</span>
					<span> {{ useTimeAgo(query.result.lastExecutedAt).value }} </span>
				</div>
			</div>
		</div>
		<div class="flex items-center gap-2">
			<Button variant="outline" :label="__('Execute')" @click="() => query.execute(true)">
				<template #prefix>
					<PlayIcon class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
			<Dropdown placement="right" :options="moreActions">
				<Button variant="outline">
					<template #icon>
						<MoreHorizontal class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</Dropdown>
		</div>
	</div>

	<ViewSQLDialog v-if="showViewSQLDialog" v-model="showViewSQLDialog" />
	<ExplainPlanDialog v-if="showExplainDialog" v-model="showExplainDialog" />
</template>
