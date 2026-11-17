<script setup lang="ts">
import { Building2, CircleUser, DatabaseZap, KeyRound, SettingsIcon, Users } from 'lucide-vue-next'
import { defineAsyncComponent, shallowRef } from 'vue'
import TabbedSidebarLayout, { Tab, TabGroup } from '../components/TabbedSidebarLayout.vue'
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
const activeTab = shallowRef<Tab>(tabs.find((tab) => tab.label === props.tab) ?? tabs[0])
</script>

<template>
	<Dialog v-model:open="showDialog" size="4xl" bare>
		<template #default>
			<div class="relative flex text-base" :style="{ height: 'calc(100vh - 12rem)' }">
				<TabbedSidebarLayout
					:title="__('Settings')"
					:tabs="tabGroups"
					v-model:activeTab="activeTab"
				/>
			</div>
		</template>
	</Dialog>
</template>
