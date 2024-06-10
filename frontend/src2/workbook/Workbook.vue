<script setup lang="ts">
import ContentEditable from '@/components/ContentEditable.vue'
import { Badge } from 'frappe-ui'
import { provide, watch, watchEffect } from 'vue'
import ChartBuilder from '../charts/ChartBuilder.vue'
import Navbar from '../components/Navbar.vue'
import DashboardBuilder from '../dashboard/DashboardBuilder.vue'
import QueryBuilder from '../query/QueryBuilder.vue'
import WorkbookSidebar from './WorkbookSidebar.vue'
import useWorkbook, { workbookKey } from './workbook'

const props = defineProps<{ name: string }>()

const workbook = useWorkbook(props.name)
provide(workbookKey, workbook)

const stopWatcher = watch(
	() => workbook.isdirty,
	(dirty) => {
		if (dirty) {
			window.onbeforeunload = () => {
				return 'Are you sure you want to leave? You have unsaved changes.'
			}
			stopWatcher()
		}
	}
)

watchEffect(() => {
	document.title = `${workbook.doc.title} | Workbook`
})
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<Navbar>
			<template #left>
				<div class="flex gap-3">
					<ContentEditable
						class="rounded-sm text-lg font-medium !text-gray-800 focus:ring-2 focus:ring-gray-700 focus:ring-offset-4"
						v-model="workbook.doc.title"
						placeholder="Untitled Workbook"
					></ContentEditable>
					<Badge v-if="workbook.islocal || workbook.isdirty" theme="orange">
						Unsaved
					</Badge>
				</div>
			</template>
			<template #actions>
				<div class="flex gap-2">
					<Button
						v-show="!workbook.islocal && workbook.isdirty"
						variant="outline"
						@click="workbook.discard()"
					>
						Discard
					</Button>
					<Button
						v-show="workbook.islocal || workbook.isdirty"
						variant="solid"
						:loading="workbook.saving"
						@click="workbook.save()"
					>
						Save
					</Button>
				</div>
			</template>
		</Navbar>
		<div class="relative flex flex-1 overflow-hidden bg-gray-50">
			<WorkbookSidebar />
			<QueryBuilder
				v-if="workbook.activeQuery"
				:key="workbook.activeQuery.name"
				:query="workbook.activeQuery"
			/>
			<ChartBuilder
				v-if="workbook.activeChart"
				:key="workbook.activeChart.name"
				:chart="workbook.activeChart"
				:queries="workbook.doc.queries"
			/>
			<DashboardBuilder
				v-if="workbook.activeDashboard"
				:key="workbook.activeDashboard.name"
				:dashboard="workbook.activeDashboard"
				:charts="workbook.doc.charts"
				:queries="workbook.doc.queries"
			/>
			<div
				class="pointer-events-none absolute z-10 flex h-full w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm transition-all"
				:class="workbook.loading ? 'opacity-100' : 'opacity-0'"
			>
				<LoadingIndicator class="h-8 w-8 text-gray-700" />
			</div>
		</div>
	</div>
</template>
