<script setup>
import VueGridLayout from '@/dashboard/VueGridLayout.vue'
import usePublicDashboard from '@/dashboard/usePublicDashboard'
import BaseLayout from '@/layouts/BaseLayout.vue'
import { provide } from 'vue'
import DashboardEmptyState from './DashboardEmptyState.vue'
import PublicDashboardItem from './PublicDashboardItem.vue'

const props = defineProps({ public_key: String })
const dashboard = usePublicDashboard(props.public_key)
provide('dashboard', dashboard)
</script>

<template>
	<BaseLayout>
		<template #navbar>
			<div class="whitespace-nowrap px-1.5 text-2xl font-medium">
				{{ dashboard.doc.title }}
			</div>
		</template>

		<template #content>
			<div class="h-full w-full overflow-y-auto bg-white px-4 py-2">
				<div
					ref="gridLayout"
					class="dashboard relative flex h-fit min-h-screen w-full flex-1 flex-col"
				>
					<VueGridLayout
						:key="JSON.stringify(dashboard.itemLayouts)"
						class="h-fit w-full"
						:items="dashboard.doc.items"
						:disabled="true"
						v-model:layouts="dashboard.itemLayouts"
					>
						<template #item="{ item }">
							<PublicDashboardItem :item="item" :key="item.item_id" />
						</template>
					</VueGridLayout>

					<DashboardEmptyState
						v-if="!dashboard.doc.items.length"
						class="absolute left-1/2 top-1/2 mx-auto -translate-x-1/2 -translate-y-1/2 transform"
					/>
				</div>
			</div>
		</template>
	</BaseLayout>
</template>
