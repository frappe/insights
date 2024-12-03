<script setup lang="ts">
import { Building2, CircleUser, DatabaseZap, KeyRound, SettingsIcon, Users } from 'lucide-vue-next'
import { defineAsyncComponent, ref } from 'vue'
import TabbedSidebarLayout, { Tab, TabGroup } from '../components/TabbedSidebarLayout.vue'

const showDialog = defineModel({ required: true, default: false })
const tabGroups: TabGroup[] = [
	{
		groupLabel: 'Account',
		tabs: [
			{
				label: 'Profile',
				icon: CircleUser,
				component: defineAsyncComponent(() => import('./ProfileSettings.vue')),
			},
		],
	},
	{
		groupLabel: 'Organization',
		tabs: [
			{
				label: 'General',
				icon: SettingsIcon,
				component: defineAsyncComponent(() => import('./GeneralSettings.vue')),
			},
			// {
			// 	label: 'Email Accounts',
			// 	icon: Mail,
			// 	component: () => {},
			// },
			{
				label: 'Users',
				icon: Users,
				component: defineAsyncComponent(() => import('./UsersSettings.vue')),
			},
			{
				label: 'Permissions',
				icon: KeyRound,
				component: defineAsyncComponent(() => import('./PermissionsSettings.vue')),
			},
			{
				label: 'Data Store',
				icon: DatabaseZap,
				component: defineAsyncComponent(() => import('./DataStoreSettings.vue')),
			},
		],
	},
]
const activeTab = ref<Tab>(tabGroups[0].tabs[0])
</script>

<template>
	<Dialog v-model="showDialog" :options="{ size: '4xl' }">
		<template #body>
			<div class="relative flex text-base" :style="{ height: 'calc(100vh - 12rem)' }">
				<TabbedSidebarLayout
					title="Settings"
					:tabs="tabGroups"
					v-model:activeTab="activeTab"
				/>
			</div>
		</template>
	</Dialog>
</template>
