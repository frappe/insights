<script setup lang="ts">
import {
	CircleUser,
	DatabaseZap,
	KeyRound,
	PackageOpen,
	SettingsIcon,
	Users,
} from 'lucide-vue-next'
import { defineAsyncComponent, shallowRef } from 'vue'
import TabbedSidebarLayout, { Tab, TabGroup } from '../components/TabbedSidebarLayout.vue'
import session from '../session'
import { __ } from '../translation'

const showDialog = defineModel({ required: true, default: false })

// The migrator writes documents, so it is admin-only - the endpoints gate on it
// too. A site with no v2 rows has nothing to migrate, so the tab stays out of
// the way rather than offering an empty list.
const showMigration = session.user.is_admin && session.user.is_v2_instance

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
			...(showMigration
				? [
						{
							label: __('Migrate from v2'),
							icon: PackageOpen,
							component: defineAsyncComponent(
								() => import('./V2MigrationSettings.vue'),
							),
						},
				  ]
				: []),
		],
	},
]
const activeTab = shallowRef<Tab>(tabGroups[0].tabs[0])
</script>

<template>
	<Dialog v-model="showDialog" :options="{ size: '4xl' }">
		<template #body>
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
