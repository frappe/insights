<script setup lang="ts">
import { ref } from 'vue'
import ContentEditable from '../components/ContentEditable.vue'
import { __ } from '../translation'
import type { WorkbookChart } from '../types/workbook.types'
import { useDashboardBuilder } from './builder'
import useDashboard from './dashboard'
import DashboardActions from './DashboardActions.vue'
import DashboardBody from './DashboardBody.vue'
import DashboardEditActions from './DashboardEditActions.vue'
import DashboardItem from './DashboardItem.vue'
import EditableGridLayout from './EditableGridLayout.vue'

// A dashboard in its workbook. It adds one thing to what other pages show: the
// workbook's charts, which the owner can place on the dashboard.
//
// It renders its own header instead of mounting `DashboardPage`. The workbook's
// navbar is already above it. A second header with a border under it would look
// like two stacked navbars, so only the title sits here.
const props = defineProps<{
	dashboard_name: string
	charts: WorkbookChart[]
}>()

const dashboard = useDashboardBuilder(props.dashboard_name, props.charts)
const store = useDashboard(props.dashboard_name)

function rename(title: string) {
	store.doc.title = title
}

// `DashboardEditActions` sits beside the dashboard's actions, not among them,
// because only the builder has edit actions.
const body = ref<InstanceType<typeof DashboardBody>>()
</script>

<template>
	<div class="flex h-full w-full flex-col overflow-hidden">
		<!-- the first card's own 8px inset completes the query view's 12px gap -->
		<div class="flex h-7 flex-shrink-0 items-center justify-between gap-2 mx-4 mt-3 mb-1">
			<ContentEditable
				class="-ml-2 cursor-text text-lg-semibold !text-ink-gray-7"
				:modelValue="dashboard.title"
				@returned="rename"
				@blur="rename"
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
