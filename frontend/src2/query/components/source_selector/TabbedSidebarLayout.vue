<script setup lang="ts">
import { computed } from 'vue'
import SidebarLink from '../../../components/SidebarLink.vue'

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
			<h1 v-if="props.title" class="mb-3 px-2 pt-2 text-lg font-semibold">
				{{ props.title }}
			</h1>
			<div v-for="group in tabGroups" class="flex flex-col overflow-hidden">
				<div
					v-if="group.groupLabel"
					class="mb-2 mt-3 flex flex-shrink-0 cursor-pointer gap-1.5 px-2 text-base font-medium text-gray-600 transition-all duration-300 ease-in-out"
				>
					<span>{{ group.groupLabel }}</span>
				</div>
				<nav class="flex-1 space-y-1 overflow-y-scroll">
					<SidebarLink
						v-for="tab in group.tabs"
						:icon="tab.icon"
						:label="tab.label"
						class="w-full"
						:class="
							activeTab?.label == tab.label
								? 'bg-white shadow-sm'
								: 'hover:bg-gray-100'
						"
						@click="activeTab = tab"
					/>
				</nav>
			</div>
		</div>
		<div class="flex h-full flex-1 flex-col px-3 py-3">
			<component v-if="activeTab && activeTab.component" :is="activeTab.component" />
		</div>
	</div>
</template>
