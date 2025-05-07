<template>
	<div
		class="flex h-full flex-col justify-between transition-all duration-300 ease-in-out"
		:class="isSidebarCollapsed ? 'w-12' : 'w-56'"
	>
		<div class="flex flex-col overflow-hidden">
			<UserDropdown class="p-2" :isCollapsed="isSidebarCollapsed" />
			<div class="flex flex-col overflow-y-auto">
				<template v-for="link in links">
					<SidebarLink
						v-if="!link.hidden"
						class="mx-2 my-0.5"
						:icon="link.icon"
						:label="link.label"
						:to="link.to"
						:isCollapsed="isSidebarCollapsed"
						@click="link.onClick"
					/>
				</template>
			</div>
		</div>
		<div>
			<TrialBanner v-if="is_fc_site" :is-sidebar-collapsed="isSidebarCollapsed" />
			<SidebarLink
				:label="isSidebarCollapsed ? 'Expand' : 'Collapse'"
				:isCollapsed="isSidebarCollapsed"
				@click="isSidebarCollapsed = !isSidebarCollapsed"
				class="m-2"
			>
				<template #icon>
					<span class="grid h-5 w-6 flex-shrink-0 place-items-center">
						<PanelRightOpen
							class="h-4.5 w-4.5 text-gray-700 duration-300 ease-in-out"
							:class="{ '[transform:rotateY(180deg)]': isSidebarCollapsed }"
							stroke-width="1.5"
						/>
					</span>
				</template>
			</SidebarLink>
		</div>
	</div>

	<Settings v-model="showSettingsDialog" />
</template>

<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import {
	Book,
	Database,
	DatabaseZap,
	LayoutGrid,
	PanelRightOpen,
	SettingsIcon,
} from 'lucide-vue-next'
import { computed, ref } from 'vue'
import useSettings from '../settings/settings'
import Settings from '../settings/Settings.vue'
import SidebarLink from './SidebarLink.vue'
import UserDropdown from './UserDropdown.vue'
import { TrialBanner } from 'frappe-ui/frappe'

const isSidebarCollapsed = useStorage('insights:sidebarCollapsed', false)
const showSettingsDialog = ref(false)

const settings = useSettings()
const is_fc_site = window.is_fc_site

const links = ref([
	{
		label: 'Dashboards',
		icon: LayoutGrid,
		to: 'DashboardList',
	},
	{
		label: 'Workbooks',
		icon: Book,
		to: 'WorkbookList',
	},
	{
		label: 'Data Sources',
		icon: Database,
		to: 'DataSourceList',
	},
	{
		label: 'Data Store',
		icon: DatabaseZap,
		to: 'DataStoreList',
		hidden: computed(() => !settings.doc.enable_data_store),
	},
	{
		label: 'Settings',
		icon: SettingsIcon,
		to: 'Settings',
		onClick: () => (showSettingsDialog.value = true),
	},
])
</script>
