<script setup lang="ts">
import { Button, Dropdown } from 'frappe-ui'
import {
	BellRing,
	Copy,
	CopyPlus,
	MoreHorizontal,
	PlayIcon,
	RefreshCw,
	Scroll,
} from 'lucide-vue-next'
import { computed, h, inject, ref } from 'vue'
import { formatShortcut } from '../../composables/useShortcut'
import session from '../../session'
import { __ } from '../../translation'
import { duplicateWorkbookItem } from '../../workbook/workbook_items'
import { Query } from '../query'
import QueryAlerts from './QueryAlerts.vue'
import ViewSQLDialog from './ViewSQLDialog.vue'

// What an editor can do to its query, in the result pane's header: run it, and
// everything else behind one menu. There is no toolbar of its own — the pane is
// the only row.
const props = withDefaults(
	defineProps<{
		onExecute?: () => void
		/** the editor's own menu items, above the ones every query has */
		extraActions?: () => any[]
		/** a result that no longer answers the editor asks to be run again */
		stale?: boolean
	}>(),
	{ onExecute: undefined, extraActions: undefined },
)

const query = inject('query') as Query

const showViewSQLDialog = ref(false)
const showAlertsDialog = ref(false)

const icon = (component: any) =>
	h(component, { class: 'h-3.5 w-3.5 text-ink-gray-6', strokeWidth: 1.5 })

const moreActions = computed(() => {
	const actions: any[] = []

	if (!query.doc.use_live_connection && session.user.is_admin) {
		actions.push({
			label: __('Refresh Stored Tables'),
			icon: icon(RefreshCw),
			onClick: query.refreshStoredTables,
		})
	}

	if (props.extraActions) {
		actions.push(...props.extraActions())
	}

	actions.push(
		{
			label: __('View SQL'),
			icon: icon(Scroll),
			onClick: () => (showViewSQLDialog.value = true),
		},
		{
			label: __('Alerts'),
			icon: icon(BellRing),
			onClick: () => (showAlertsDialog.value = true),
		},
		{
			label: __('Duplicate Query'),
			icon: icon(CopyPlus),
			onClick: () => duplicateWorkbookItem(query, 'query'),
		},
		{
			label: __('Copy Query'),
			icon: icon(Copy),
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
	<!-- stale is the only state that asks for a run, so the button says so -->
	<Button
		:variant="props.stale ? 'solid' : 'outline'"
		:label="__('Execute')"
		:tooltip="__('Execute ({0})', formatShortcut('Meta+E'))"
		@click="handleExecute"
	>
		<template #prefix>
			<PlayIcon
				class="h-3.5 w-3.5"
				:class="props.stale ? '' : 'text-ink-gray-6'"
				stroke-width="1.5"
			/>
		</template>
	</Button>

	<Dropdown align="end" :options="moreActions">
		<Button variant="outline" :tooltip="__('More')">
			<template #icon>
				<MoreHorizontal class="h-3.5 w-3.5 text-ink-gray-6" stroke-width="1.5" />
			</template>
		</Button>
	</Dropdown>

	<ViewSQLDialog v-if="showViewSQLDialog" v-model="showViewSQLDialog" />
	<QueryAlerts v-model="showAlertsDialog" :query="query" />
</template>
