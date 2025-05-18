<script setup lang="ts">
import { useMagicKeys, whenever } from '@vueuse/core'
import { AlertOctagon } from 'lucide-vue-next'
import { provide, watchEffect } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import LoadingOverlay from '../components/LoadingOverlay.vue'
import { waitUntil } from '../helpers'
import useWorkbook, { workbookKey } from './workbook'
import WorkbookNavbar from './WorkbookNavbar.vue'
import WorkbookSidebar from './WorkbookSidebar.vue'

defineOptions({ inheritAttrs: false })

const props = defineProps<{ workbook_name: string }>()

const workbook = useWorkbook(props.workbook_name)
provide(workbookKey, workbook)
window.workbook = workbook

await waitUntil(() => workbook.isloaded)

if (workbook.doc.queries.length === 0) {
	workbook.addQuery()
}

const router = useRouter()
const route = useRoute()
if (route.name === 'Workbook' && workbook.doc.queries.length) {
	const query = workbook.doc.queries[0]
	router.replace(`/workbook/${workbook.doc.name}/query/${query.name}`)
}

const keys = useMagicKeys()
const cmdS = keys['Meta+S']
whenever(cmdS, () => workbook.save())

const cmdV = keys['Meta+V']
whenever(cmdV, () => {
	if (!navigator.clipboard) {
		return
	}
	navigator.clipboard.readText().then((text) => {
		try {
			const json = JSON.parse(text)
			if (json.type === 'Query') {
				workbook.importQuery(json)
			} else if (json.type === 'Chart') {
				workbook.importChart(json)
			}
		} catch (e) {}
	})
})

watchEffect(() => {
	document.title = `${workbook.doc.title} | Workbook`
})
</script>

<template>
	<div class="flex h-full w-full flex-col">
		<LoadingOverlay v-if="!workbook.isloaded" />
		<WorkbookNavbar />
		<div
			class="relative flex w-full flex-1 overflow-hidden"
			:class="workbook.showSidebar ? 'flex-row' : 'flex-col'"
		>
			<WorkbookSidebar />
			<RouterView v-if="workbook.isloaded" :key="route.fullPath" v-slot="{ Component }">
				<component :is="Component" />
				<div v-if="false" class="flex flex-1 items-center justify-center">
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
