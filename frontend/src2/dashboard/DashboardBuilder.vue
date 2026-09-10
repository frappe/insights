<script setup lang="ts">
import { ref } from 'vue'
import ContentEditable from '../components/ContentEditable.vue'
import { __ } from '../translation'
import type { WorkbookChart } from '../types/workbook.types'
import { useDashboardBuilder } from './builder'
import DashboardActions from './DashboardActions.vue'
import DashboardBody from './DashboardBody.vue'
import DashboardEditActions from './DashboardEditActions.vue'
import DashboardItem from './DashboardItem.vue'
import EditableGridLayout from './EditableGridLayout.vue'

// A dashboard inside the workbook that owns it. It shows what every other
// surface shows, so all it adds is the one thing only the workbook knows: which
// charts this dashboard may draw from.
//
// It draws its own header instead of mounting `DashboardPage`. The workbook's
// navbar is already above it, so a second band with a rule under it reads as two
// navbars stacked, and the rule has no left edge to meet. What belongs here is
// the dashboard's own title, sitting in the dashboard rather than over it.
const props = defineProps<{
	dashboard_name: string
	charts: WorkbookChart[]
}>()

const dashboard = useDashboardBuilder(props.dashboard_name, props.charts)

// the dashboard's own actions, read where it is drawn. `DashboardEditActions` is
// beside them and not among them: the edit chrome is this surface's, and only
// this surface has one.
const body = ref<InstanceType<typeof DashboardBody>>()
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden">
		<!-- the first card's own 8px inset completes the query view's 12px gap -->
		<div class="flex h-7 flex-shrink-0 items-center justify-between gap-2 mx-4 mt-3 mb-1">
			<ContentEditable
				class="-ml-2 cursor-text text-lg-semibold !text-ink-gray-7"
				:modelValue="dashboard.title"
				@returned="dashboard.builder.rename($event)"
				@blur="dashboard.builder.rename($event)"
				:placeholder="__('Untitled Dashboard')"
			/>

			<div v-if="!dashboard.loading" class="flex flex-shrink-0 items-center gap-2">
				<DashboardEditActions />
				<DashboardActions :actions="body?.actions || []" />
			</div>
		</div>

		<DashboardBody
			ref="body"
			class="min-h-0 flex-1"
			:dashboard="dashboard"
			:grid="EditableGridLayout"
			:cell="DashboardItem"
		/>
	</div>
</template>
