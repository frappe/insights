<script setup lang="ts">
import { provide, watch, watchEffect } from 'vue'
import ChartBuilder from '../charts/ChartBuilder.vue'
import Navbar from '../components/Navbar.vue'
import QueryBuilder from '../query/QueryBuilder.vue'
import WorkbookSidebar from './WorkbookSidebar.vue'
import useWorkbook, { workbookKey } from './workbook'

const props = defineProps<{ name: string }>()

const workbook = useWorkbook(props.name)
provide(workbookKey, workbook)

// if (props.name.startsWith('new-workbook')) {
// 	window.onbeforeunload = () => {
// 		return 'Are you sure you want to leave? You have unsaved changes.'
// 	}
// }

watchEffect(() => {
	document.title = `${workbook.doc.name} | Workbook`
})
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<Navbar>
			<template #actions>
				<div class="flex gap-2">
					<Button variant="outline" icon-left="save" @click="workbook.save()">
						Save
					</Button>
				</div>
			</template>
		</Navbar>
		<div class="relative flex flex-1 overflow-hidden bg-gray-50">
			<WorkbookSidebar />
			<QueryBuilder
				v-if="workbook.activeTabType === 'query'"
				:key="workbook.activeTabName"
				:query-id="workbook.activeTabName"
			/>
			<ChartBuilder
				v-if="workbook.activeTabType === 'chart'"
				:key="workbook.activeTabName"
				:chart-id="workbook.activeTabName"
				:queries="workbook.doc.queries.map((q) => q.query)"
			/>

			<div
				v-if="workbook.loading"
				class="absolute z-10 flex h-full w-full items-center justify-center rounded bg-gray-50/30 backdrop-blur-sm"
			>
				<LoadingIndicator class="h-8 w-8 text-gray-700" />
			</div>
		</div>
	</div>
</template>
