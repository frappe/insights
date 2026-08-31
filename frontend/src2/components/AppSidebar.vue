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
			<DemoDataBanner v-if="!isSidebarCollapsed" class="m-2 p-2" />
			<V2MigrationBanner v-if="!isSidebarCollapsed" class="m-2 p-2" />
			<TrialBanner v-if="is_fc_site" :is-sidebar-collapsed="isSidebarCollapsed" />
			<SidebarLink
				:label="isSidebarCollapsed ? __('Expand') : __('Collapse')"
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
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import useSettings, {
	settingsOpenedFrom,
	settingsTab,
	showSettingsDialog,
} from '../settings/settings'
import Settings from '../settings/Settings.vue'
import SidebarLink from './SidebarLink.vue'
import DemoDataBanner from './DemoDataBanner.vue'
import V2MigrationBanner from './V2MigrationBanner.vue'
import UserDropdown from './UserDropdown.vue'
import { TrialBanner } from 'frappe-ui/frappe'
import { __ } from '../translation'

const isSidebarCollapsed = useStorage('insights:sidebarCollapsed', false)

const settings = useSettings()
const is_fc_site = window.is_fc_site

// `?settings=<tab>` opens the dialog on that tab. The settings live in a dialog
// and not on a route, so this is the only way another app - v2 - can link into
// one. The param is cleared, or a reload would reopen the dialog.
const route = useRoute()
const router = useRouter()
onMounted(() => {
	const tab = route.query.settings
	if (!tab) return
	settingsTab.value = String(tab)
	// Only v2 links in, so the param is the whole of what "came from v2" means.
	settingsOpenedFrom.value = 'v2'
	showSettingsDialog.value = true
	const query = { ...route.query }
	delete query.settings
	router.replace({ query })
})

const links = ref([
	{
		label: __('Dashboards'),
		icon: LayoutGrid,
		to: 'DashboardList',
	},
	{
		label: __('Workbooks'),
		icon: Book,
		to: 'WorkbookList',
	},
	{
		label: __('Data Sources'),
		icon: Database,
		to: 'DataSourceList',
	},
	{
		label: __('Data Store'),
		icon: DatabaseZap,
		to: 'DataStoreList',
		hidden: computed(() => !settings.doc.enable_data_store),
	},
	{
		label: __('Settings'),
		icon: SettingsIcon,
		onClick: () => (showSettingsDialog.value = true),
	},
])
</script>
