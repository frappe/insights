<script setup lang="ts">
import { Copy, CopyPlus, MoreHorizontal, PlayIcon, RefreshCw, Scroll } from 'lucide-vue-next'
import { computed, h, inject, ref } from 'vue'
import { Tooltip } from 'frappe-ui'
import { formatShortcut } from '../../composables/useShortcut'
import session from '../../session'
import { __ } from '../../translation'
import { Query } from '../query'
import ViewSQLDialog from './ViewSQLDialog.vue'

const props = withDefaults(
	defineProps<{
		onExecute?: () => void
		extraActions?: () => any[]
	}>(),
	{ onExecute: undefined, extraActions: undefined },
)

const query = inject('query') as Query

const showViewSQLDialog = ref(false)

const moreActions = computed(() => {
	const actions: any[] = []

	if (!query.doc.use_live_connection && session.user.is_admin) {
		actions.push({
			label: __('Refresh Stored Tables'),
			icon: h(RefreshCw, { class: 'h-3 w-3 text-gray-700', strokeWidth: 1.5 }),
			onClick: query.refreshStoredTables,
		})
	}

	if (props.extraActions) {
		actions.push(...props.extraActions())
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

function handleExecute() {
	props.onExecute ? props.onExecute() : query.execute(true)
}
</script>

<template>
	<div class="flex w-full flex-shrink-0 items-center justify-between bg-white">
		<slot />
		<div class="flex items-center gap-2">
			<Tooltip :text="__('Execute ({0})', formatShortcut('Meta+E'))">
				<Button variant="outline" :label="__('Execute')" @click="handleExecute">
					<template #prefix>
						<PlayIcon class="h-3.5 w-3.5 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</Tooltip>
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
</template>
