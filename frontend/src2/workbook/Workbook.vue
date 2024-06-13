<script setup lang="ts">
import ContentEditable from '@/components/ContentEditable.vue'
import { useMagicKeys, whenever } from '@vueuse/core'
import { Badge } from 'frappe-ui'
import { provide, watch, watchEffect } from 'vue'
import { useRoute } from 'vue-router'
import Navbar from '../components/Navbar.vue'
import WorkbookSidebar from './WorkbookSidebar.vue'
import useWorkbook, { workbookKey } from './workbook'

const props = defineProps<{ name: string }>()
const route = useRoute()

const workbook = useWorkbook(props.name)
provide(workbookKey, workbook)

const keys = useMagicKeys()
const cmdS = keys['Meta+S']
whenever(cmdS, () => workbook.save())

watch(
	() => workbook.isdirty,
	(dirty) => (window.onbeforeunload = dirty ? function () {} : null)
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
			<RouterView :key="route.fullPath" />
		</div>
	</div>
</template>
