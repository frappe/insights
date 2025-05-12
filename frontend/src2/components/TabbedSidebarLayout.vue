<script setup lang="ts">
import { computed } from 'vue'
import SidebarLink from './SidebarLink.vue'

export type Tab = {
	label: string
	component?: any
	icon?: any
}
export type TabGroup = {
	groupLabel: string
	tabs: Tab[]
}
export type Tabs = Tab[] | TabGroup[]
const props = defineProps<{ title?: string; tabs: Tabs }>()

const tabGroups = computed(() => {
	if (!props.tabs.length) {
		return []
	}
	if (props.tabs[0].hasOwnProperty('tabs')) {
		return props.tabs as TabGroup[]
	}
	return [{ groupLabel: '', tabs: props.tabs as Tab[] }]
})

const activeTab = defineModel<Tab>('activeTab', {
	type: Object,
})
</script>

<template>
	<div class="flex h-full w-full">
		<div class="flex w-52 shrink-0 flex-col overflow-hidden bg-gray-50 p-2">
			<h1 v-if="props.title" class="px-2 pt-2 text-lg font-semibold">
				{{ props.title }}
			</h1>
			<div v-for="group in tabGroups" class="flex min-h-[6rem] flex-col overflow-hidden">
				<div
					v-if="group.groupLabel"
					class="mb-2 mt-4 flex flex-shrink-0 px-2 text-sm font-medium text-gray-600"
				>
					<span>{{ group.groupLabel }}</span>
				</div>
				<nav class="flex-1 space-y-1 overflow-y-scroll p-0.5">
					<SidebarLink
						v-for="tab in group.tabs"
						:icon="tab.icon"
						:label="tab.label"
						class="w-full"
						:is-active="activeTab?.label == tab.label"
						@click="activeTab = tab"
					/>
				</nav>
			</div>
		</div>
		<div class="flex h-full flex-1 flex-col overflow-hidden">
			<component v-if="activeTab && activeTab.component" :is="activeTab.component" />
		</div>
	</div>
</template>
