<script setup lang="ts">
import { Breadcrumbs } from 'frappe-ui'
import { ExternalLink, RefreshCcw } from 'lucide-vue-next'
import { provide } from 'vue'
import { useRouter } from 'vue-router'
import { waitUntil } from '../helpers'
import useWorkbook from '../workbook/workbook'
import useDashboard from './dashboard'
import DashboardFilterSelector from './DashboardFilterSelector.vue'
import DashboardItem from './DashboardItem.vue'
import useDashboardStore from './dashboards'
import VueGridLayout from './VueGridLayout.vue'

const props = defineProps<{ name: string }>()

const store = useDashboardStore()
const workbookName = await store.fetchWorkbookName(props.name)

const workbook = useWorkbook(workbookName)
await waitUntil(() => workbook.doc.dashboards.length > 0)

const dashboard = useDashboard(
	workbook.doc.dashboards.find((dashboard) => dashboard.name === props.name)!
)
provide('dashboard', dashboard)
dashboard.refresh()

const router = useRouter()
function openWorkbook() {
	router.push(`/workbook/${workbook.doc.name}`)
}
</script>

<template>
	<header class="flex h-12 items-center justify-between border-b py-2.5 pl-5 pr-2">
		<Breadcrumbs
			:items="[
				{ label: 'Dashboards', route: '/dashboards' },
				{ label: dashboard.doc.title, route: `/dashboards/${dashboard.doc.name}` },
			]"
		/>
		<div class="flex items-center gap-2">
			<DashboardFilterSelector
				:dashboard="dashboard"
				:queries="workbook.doc.queries"
				:charts="workbook.doc.charts"
			/>
			<Button variant="outline" @click="() => dashboard.refresh()" label="Refresh">
				<template #prefix>
					<RefreshCcw class="h-4 w-4 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
			<Button variant="outline" @click="openWorkbook" label="Workbook">
				<template #prefix>
					<ExternalLink class="h-4 w-4 text-gray-700" stroke-width="1.5" />
				</template>
			</Button>
		</div>
	</header>

	<div class="relative flex h-full w-full overflow-hidden">
		<div class="flex-1 overflow-y-auto p-4">
			<VueGridLayout
				v-if="dashboard.doc.items.length > 0"
				class="h-fit w-full"
				:cols="20"
				:disabled="true"
				:modelValue="dashboard.doc.items.map((item) => item.layout)"
			>
				<template #item="{ index }">
					<DashboardItem :index="index" :item="dashboard.doc.items[index]" />
				</template>
			</VueGridLayout>
		</div>
	</div>
</template>
