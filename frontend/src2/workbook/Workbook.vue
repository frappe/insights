<script setup lang="ts">
import { useMagicKeys, whenever } from '@vueuse/core'
import { Badge } from 'frappe-ui'
import { AlertOctagon, ArrowLeft } from 'lucide-vue-next'
import { computed, provide, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import ContentEditable from '../components/ContentEditable.vue'
import Navbar from '../components/Navbar.vue'
import useWorkbook, { workbookKey } from './workbook'
import WorkbookNavbarActions from './WorkbookNavbarActions.vue'
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

watchEffect(() => {
	document.title = `${workbook.doc.title} | Workbook`
})
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<Navbar>
			<template #left>
				<Button variant="ghost" @click="router.push('/')">
					<template #icon>
						<ArrowLeft class="h-4 w-4" stroke-width="1.5" />
					</template>
				</Button>
			</template>
			<template #center>
				<div class="flex gap-3">
					<ContentEditable
						class="rounded-sm font-medium !text-gray-800 focus:ring-2 focus:ring-gray-700 focus:ring-offset-4"
						v-model="workbook.doc.title"
						placeholder="Untitled Workbook"
					></ContentEditable>
					<Badge size="sm" v-if="workbook.islocal || workbook.isdirty" theme="orange">
						Unsaved
					</Badge>
				</div>
			</template>
			<template #right>
				<WorkbookNavbarActions />
			</template>
		</Navbar>
		<div
			class="relative flex w-full flex-1 overflow-hidden bg-gray-50"
			:class="workbook.showSidebar ? 'flex-row' : 'flex-col'"
		>
			<WorkbookSidebar v-if="workbook.showSidebar" />
			<WorkbookTabSwitcher v-else />
			<RouterView :key="route.fullPath" v-slot="{ Component }">
				<component v-if="tabExists" :is="Component" />
				<div v-else class="flex flex-1 items-center justify-center">
					<div class="flex flex-col items-center gap-4">
						<AlertOctagon class="h-16 w-16 text-gray-400" stroke-width="1" />
						<p class="text-center text-lg text-gray-500">
							Looks like this tab doesn't exist <br />
							Try switching to another tab
						</p>
					</div>
				</div>
			</RouterView>
		</div>
	</div>
</template>
