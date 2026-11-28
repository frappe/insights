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
			<UpgradeCard v-if="!isSidebarCollapsed" class="m-2" />
			<SecurityUpdateCard v-if="!isSidebarCollapsed" class="m-2" />
			<TrialBanner v-if="isFCSite" :is-sidebar-collapsed="isSidebarCollapsed" />
			<SidebarLink
				:label="isSidebarCollapsed ? __('Expand') : __('Collapse')"
				:isCollapsed="isSidebarCollapsed"
				@click="isSidebarCollapsed = !isSidebarCollapsed"
				class="m-2"
			>
				<template #icon>
					<span class="grid h-5 w-6 flex-shrink-0 place-items-center">
						<PanelRightOpen
							class="h-4.5 w-4.5 text-ink-gray-6 duration-300 ease-in-out"
							:class="{ '[transform:rotateY(180deg)]': isSidebarCollapsed }"
							stroke-width="1.5"
						/>
					</span>
				</template>
			</SidebarLink>
		</div>
	</div>

	<Settings v-if="session.isAuthorized" v-model="showSettingsDialog" />
</template>

<script setup lang="ts">
import { useStorage } from '@vueuse/core'
import { PanelRightOpen } from 'lucide-vue-next'
import Settings from '../settings/Settings.vue'
import SidebarLink from './SidebarLink.vue'
import DemoDataBanner from './DemoDataBanner.vue'
import SecurityUpdateCard from './SecurityUpdateCard.vue'
import UpgradeCard from '../upgrade/UpgradeCard.vue'
import UserDropdown from './UserDropdown.vue'
import { TrialBanner } from '@framework/ui/components/TrialBanner/index.ts'
import { __ } from '../translation'
import session from '../session'
import { showSettingsDialog, useNavLinks } from './nav_links'
import { isFCSite } from './user_menu'

// A phone gets the tab bar instead, so this is the sidebar from `sm` up
const isSidebarCollapsed = useStorage('insights:sidebarCollapsed', false)
const links = useNavLinks()
</script>
