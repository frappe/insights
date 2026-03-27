<script setup lang="ts">
import { useTimeAgo } from '@vueuse/core'
import { Tooltip } from 'frappe-ui'
import {
	Copy,
	CopyPlus,
	MoreHorizontal,
	PlayIcon,
	RefreshCw,
	Scroll,
	Sparkles,
} from 'lucide-vue-next'
import { computed, h, inject, ref } from 'vue'
import session from '../../session'
import { __ } from '../../translation'
import { Query } from '../query'
import AIQueryDialog from './AIQueryDialog.vue'
import ViewSQLDialog from './ViewSQLDialog.vue'

const query = inject('query') as Query

const showViewSQLDialog = ref(false)
const showAIQueryDialog = ref(false)

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
			<Tooltip :text="__('Modify with AI')">
				<Button
					variant="ghost"
					@click="() => (showAIQueryDialog = true)"
					class="!h-6 !gap-1.5 bg-white !px-2 text-xs shadow"
				>
					<template #icon>
						<Sparkles class="h-3 w-3 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</Tooltip>
			<Button
				variant="ghost"
				:label="__('Execute')"
				@click="() => query.execute(true)"
				class="!h-6 !gap-1.5 bg-white !px-2 text-xs shadow"
			>
				<template #prefix>
					<PlayIcon class="h-3 w-3 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
			<Dropdown placement="right" :options="moreActions">
				<Button variant="ghost" class="!h-6 !gap-1.5 bg-white !px-2 text-xs shadow">
					<template #icon>
						<MoreHorizontal class="h-3 w-3 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</Dropdown>
		</div>
	</div>

	<ViewSQLDialog v-if="showViewSQLDialog" v-model="showViewSQLDialog" />
	<AIQueryDialog v-if="showAIQueryDialog" v-model="showAIQueryDialog" />
</template>
