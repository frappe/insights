<template>
	<div
		class="flex h-full flex-col justify-between transition-all duration-300 ease-in-out"
		:class="isSidebarCollapsed ? 'w-12' : 'w-56'"
	>
		<div class="flex flex-col overflow-hidden">
			<UserDropdown class="p-2" :isCollapsed="isSidebarCollapsed" />
			<div class="flex flex-col overflow-y-auto">
				<SidebarLink
					v-for="link in links"
					class="mx-2 my-0.5"
					:icon="link.icon"
					:label="link.label"
					:to="link.to"
					:isCollapsed="isSidebarCollapsed"
					@click="link.onClick"
				/>
			</div>
		</div>
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

	<Settings v-model="showSettingsDialog" />
</template>

<script setup lang="ts">
import {
	Book,
	Database,
	DatabaseZap,
	LayoutGrid,
	PanelRightOpen,
	SettingsIcon,
	Warehouse,
} from 'lucide-vue-next'
import { ref } from 'vue'
import Settings from '../settings/Settings.vue'
import SidebarLink from './SidebarLink.vue'
import UserDropdown from './UserDropdown.vue'

const isSidebarCollapsed = ref(false)
const showSettingsDialog = ref(false)

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
	},
	{
		label: 'Settings',
		icon: SettingsIcon,
		to: 'Settings',
		onClick: () => (showSettingsDialog.value = true),
	},
])
</script>
