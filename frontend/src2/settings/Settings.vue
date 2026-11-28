<script setup lang="ts">
import { Building2, CircleUser, DatabaseZap, KeyRound, SettingsIcon, Users } from 'lucide-vue-next'
import { defineAsyncComponent, shallowRef, watch } from 'vue'
import TabbedSidebarLayout, { Tab, TabGroup } from '../components/TabbedSidebarLayout.vue'
import { useIsMobile } from '../composables/useIsMobile'
import { __ } from '../translation'

const showDialog = defineModel({ required: true, default: false })
// the label of the tab to open on
const props = defineProps<{ tab?: string }>()
const tabGroups: TabGroup[] = [
	{
		groupLabel: __('Account'),
		tabs: [
			{
				label: __('Profile'),
				icon: CircleUser,
				component: defineAsyncComponent(() => import('./ProfileSettings.vue')),
			},
		],
	},
	{
		groupLabel: __('Organization'),
		tabs: [
			{
				label: __('General'),
				icon: SettingsIcon,
				component: defineAsyncComponent(() => import('./GeneralSettings.vue')),
			},
			// {
			// 	label: 'Email Accounts',
			// 	icon: Mail,
			// 	component: () => {},
			// },
			{
				label: __('Users'),
				icon: Users,
				component: defineAsyncComponent(() => import('./UsersSettings.vue')),
			},
			{
				label: __('Permissions'),
				icon: KeyRound,
				component: defineAsyncComponent(() => import('./PermissionsSettings.vue')),
			},
			{
				label: __('Data Store'),
				icon: DatabaseZap,
				component: defineAsyncComponent(() => import('./DataStoreSettings.vue')),
			},
		],
	},
]
const tabs = tabGroups.flatMap((group) => group.tabs)
// a phone opens on the list of tabs, unless the caller names one
const isMobile = useIsMobile()
const activeTab = shallowRef<Tab | undefined>(
	tabs.find((tab) => tab.label === props.tab) ?? (isMobile.value ? undefined : tabs[0]),
)
// a desktop always shows a tab, also when the window was a phone's at first
watch(showDialog, (open) => {
	if (open && !activeTab.value && !isMobile.value) activeTab.value = tabs[0]
})
</script>

<template>
	<Dialog v-model:open="showDialog" size="4xl" bare>
		<template #default>
			<div class="relative flex h-[calc(100vh-12rem)] text-base max-sm:h-[calc(90dvh-1rem)]">
				<TabbedSidebarLayout
					:title="__('Settings')"
					:tabs="tabGroups"
					v-model:activeTab="activeTab"
				/>
			</div>
		</template>
	</Dialog>
</template>
