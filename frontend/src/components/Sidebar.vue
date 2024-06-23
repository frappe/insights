<template>
	<div
		class="rg:w-60 flex w-14 flex-shrink-0 flex-col border-r border-gray-300 bg-white"
		v-if="currentRoute"
	>
		<div class="flex flex-grow flex-col overflow-y-auto p-2.5">
			<div class="rg:flex hidden flex-shrink-0 items-end text-sm text-gray-600">
				<img src="../assets/insights-logo-new.svg" class="h-7" />
			</div>
			<router-link to="/" class="rg:hidden flex cursor-pointer">
				<img src="../assets/insights-logo-new.svg" class="rounded" />
			</router-link>

			<div class="mt-4 flex flex-col">
				<nav class="flex-1 space-y-1 pb-4 text-base">
					<Tooltip
						v-for="route in sidebarItems"
						:key="route.path"
						placement="right"
						:hoverDelay="0.1"
						class="w-full"
					>
						<template #body>
							<div
								class="w-fit rounded border border-gray-100 bg-gray-800 px-2 py-1 text-xs text-white shadow-xl"
							>
								{{ route.label }}
							</div>
						</template>

						<router-link
							:to="route.path"
							:class="[
								route.current
									? 'bg-gray-200/70'
									: 'text-gray-700 hover:bg-gray-50 hover:text-gray-800',
								'rg:justify-start group flex w-full items-center justify-center rounded p-2 font-medium',
							]"
							aria-current="page"
						>
							<component
								:is="route.icon"
								:stroke-width="1.5"
								:class="[
									route.current
										? 'text-gray-800'
										: 'text-gray-700 group-hover:text-gray-700',
									'rg:mr-3 rg:h-4 rg:w-4 mr-0 h-5 w-5 flex-shrink-0',
								]"
							/>

							<span class="rg:inline-block hidden">{{ route.label }}</span>
						</router-link>
					</Tooltip>
				</nav>
			</div>

			<div class="mt-auto flex flex-col items-center gap-2 text-base text-gray-600">
				<Button variant="ghost" @click="open('https://docs.frappeinsights.com')">
					<BookOpen class="h-4 text-gray-600" />
				</Button>
				<Dropdown
					placement="left"
					:options="[
						{
							label: 'Documentation',
							icon: 'help-circle',
							onClick: () => open('https://docs.frappeinsights.com'),
						},
						{
							label: 'Join Telegram Group',
							icon: 'message-circle',
							onClick: () => open('https://t.me/frappeinsights'),
						},
						{
							label: 'Help',
							icon: 'life-buoy',
							onClick: () => (showHelpDialog = true),
						},
						session.user.is_admin
							? {
									label: 'Switch to Desk',
									icon: 'grid',
									onClick: () => open('/app'),
							  }
							: null,
						{
							label: 'Logout',
							icon: 'log-out',
							onClick: () => session.logout(),
						},
					]"
				>
					<template v-slot="{ open }">
						<button
							class="flex w-full items-center space-x-2 rounded p-1 text-left text-base font-medium"
							:class="open ? 'bg-gray-300' : 'hover:bg-gray-200'"
						>
							<Avatar
								size="xl"
								:label="session.user.full_name"
								:image="session.user.user_image"
							/>
							<span
								class="rg:inline ml-2 hidden overflow-hidden text-ellipsis whitespace-nowrap"
							>
								{{ session.user.full_name }}
							</span>
							<FeatherIcon name="chevron-down" class="rg:inline hidden h-4 w-4" />
						</button>
					</template>
				</Dropdown>
			</div>
		</div>
	</div>

	<HelpDialog v-model="showHelpDialog" />
</template>

<script setup>
import { Avatar } from 'frappe-ui'

import HelpDialog from '@/components/HelpDialog.vue'
import sessionStore from '@/stores/sessionStore'
import settingsStore from '@/stores/settingsStore'
import { createResource } from 'frappe-ui'
import {
	Book,
	Database,
	GanttChartSquare,
	HomeIcon,
	LayoutPanelTop,
	Settings,
	User,
	Users,
	BookOpen,
} from 'lucide-vue-next'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

const session = sessionStore()
const settings = settingsStore().settings

const showHelpDialog = ref(false)
const sidebarItems = ref([
	{
		path: '/',
		label: 'Home',
		icon: HomeIcon,
		name: 'Home',
		current: false,
	},
	{
		path: '/dashboard',
		label: 'Dashboards',
		icon: LayoutPanelTop,
		name: 'Dashboard',
		current: false,
	},
	{
		path: '/query',
		label: 'Query',
		icon: GanttChartSquare,
		name: 'QueryList',
		current: false,
	},
	{
		path: '/data-source',
		label: 'Data Sources',
		icon: Database,
		name: 'Data Source',
	},
	{
		path: '/notebook',
		label: 'Notebook',
		icon: Book,
		name: 'Notebook',
		current: false,
	},
	{
		path: '/settings',
		label: 'Settings',
		icon: Settings,
		name: 'Settings',
		current: false,
	},
])

watch(
	() => session.user.is_admin && settings?.enable_permissions,
	(isAdmin) => {
		if (isAdmin) {
			// add users & teams item after settings item
			if (sidebarItems.value.find((item) => item.name === 'Teams')) {
				return
			}
			const settingsIndex = sidebarItems.value.findIndex((item) => item.name === 'Settings')
			sidebarItems.value.splice(settingsIndex, 0, {
				path: '/users',
				label: 'Users',
				icon: User,
				name: 'Users',
				current: false,
			})
			sidebarItems.value.splice(settingsIndex + 1, 0, {
				path: '/teams',
				label: 'Teams',
				icon: Users,
				name: 'Teams',
				current: false,
			})
		}
	}
)

const route = useRoute()
const currentRoute = computed(() => {
	sidebarItems.value.forEach((item) => {
		// check if /<route> or /<route>/<id> is in sidebar item path
		item.current = route.path.match(new RegExp(`^${item.path}(/|$)`))
	})
	return route.path
})

const open = (url) => window.open(url, '_blank')
</script>
