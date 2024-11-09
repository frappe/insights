<script setup lang="ts">
import { useMagicKeys, whenever } from '@vueuse/core'
import { AlertOctagon } from 'lucide-vue-next'
import { computed, provide, watchEffect } from 'vue'
import { onBeforeRouteLeave, useRoute, useRouter } from 'vue-router'
import useWorkbook, { workbookKey } from './workbook'
import WorkbookNavbar from './WorkbookNavbar.vue'
import WorkbookSidebar from './WorkbookSidebar.vue'
import WorkbookTabSwitcher from './WorkbookTabSwitcher.vue'

defineOptions({ inheritAttrs: false })

const props = defineProps<{ name: string }>()
const router = useRouter()
const route = useRoute()

const workbook = useWorkbook(props.name)
provide(workbookKey, workbook)

const keys = useMagicKeys()
const cmdS = keys['Meta+S']
whenever(cmdS, () => workbook.save())

if (workbook.islocal && workbook.doc.queries.length === 0) {
	workbook.addQuery()
}

const tabExists = computed(() => {
	const tabType = route.name?.toString().replace('Workbook', '').toLowerCase()
	const tabIndex = parseInt(route.params.index.toString())
	return (
		(tabType === 'query' && workbook.doc.queries[tabIndex]) ||
		(tabType === 'chart' && workbook.doc.charts[tabIndex]) ||
		(tabType === 'dashboard' && workbook.doc.dashboards[tabIndex])
	)
})

onBeforeRouteLeave(() => {
	if (workbook.islocal) {
		const message = 'Do you really want to leave? you have unsaved changes!'
		if (!window.confirm(message)) {
			return false
		}
	}
})

watchEffect(() => {
	document.title = `${workbook.doc.title} | Workbook`
})
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<WorkbookNavbar />
		<div
			class="relative flex w-full flex-1 overflow-hidden"
			:class="workbook.showSidebar ? 'flex-row' : 'flex-col'"
		>
			<WorkbookSidebar v-if="workbook.showSidebar" />
			<WorkbookTabSwitcher v-else />
			<RouterView :key="route.fullPath" v-slot="{ Component }">
				<component v-if="tabExists" :is="Component" />
				<div v-else class="flex flex-1 items-center justify-center">
					<div class="flex flex-col items-center gap-4">
						<AlertOctagon class="h-16 w-16 text-gray-400" stroke-width="1" />
						<p
							v-if="workbook.doc.queries.length"
							class="text-center text-lg leading-4 text-gray-500"
						>
							This tab doesn't exist <br />
							Try switching to another tab
						</p>
						<p v-else class="text-center text-lg leading-5 text-gray-500">
							You haven't added any queries yet <br />
							Click on the "+" button to add a new query
						</p>
					</div>
				</div>
			</RouterView>
		</div>
	</div>
</template>
