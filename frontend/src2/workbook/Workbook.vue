<script setup lang="ts">
import ContentEditable from '@/components/ContentEditable.vue'
import { useMagicKeys, whenever } from '@vueuse/core'
import { Badge } from 'frappe-ui'
import { provide, watch, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import Navbar from '../components/Navbar.vue'
import useWorkbook, { workbookKey } from './workbook'
import WorkbookNavbarActions from './WorkbookNavbarActions.vue'
import WorkbookSidebar from './WorkbookSidebar.vue'

defineOptions({ inheritAttrs: false })

const props = defineProps<{ name: string }>()
const route = useRoute()

const workbook = useWorkbook(props.name)
provide(workbookKey, workbook)

const keys = useMagicKeys()
const cmdS = keys['Meta+S']
whenever(cmdS, () => workbook.save())

window.onbeforeunload = function () {
	if (workbook.isdirty) {
		return 'You have unsaved changes. Are you sure you want to leave?'
	}
}

if (workbook.islocal && workbook.doc.queries.length === 0) {
	workbook.addQuery()
}

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
				<WorkbookNavbarActions />
			</template>
		</Navbar>
		<div class="relative flex flex-1 overflow-hidden bg-gray-50">
			<WorkbookSidebar />
			<RouterView :key="route.fullPath" />
		</div>
	</div>
</template>
