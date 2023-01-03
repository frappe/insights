<script setup>
import { ref, computed } from 'vue'

const sidebarItems = ref([
	{
		label: 'Members',
		icon: 'users',
		current: true,
	},
	{
		label: 'Data Sources',
		icon: 'database',
	},
	{
		label: 'Tables',
		icon: 'table',
	},
	{
		label: 'Dashboards',
		icon: 'monitor',
	},
	{
		label: 'Queries',
		icon: 'file-text',
	},
])
const emit = defineEmits(['change'])
const currentSidebarItem = computed({
	get: () => sidebarItems.value.find((item) => item.current).label,
	set: (value) => {
		sidebarItems.value = sidebarItems.value.map((item) => {
			item.current = item.label == value
			return item
		})
		emit('change', value)
	},
})
</script>
<template>
	<div class="w-1/4 bg-gray-50 p-3 text-gray-600">
		<nav class="flex-1 space-y-1 pb-4 text-base">
			<div
				v-for="item in sidebarItems"
				:key="item.label"
				:class="[
					item.current
						? 'bg-gray-200/70'
						: 'text-gray-600 hover:bg-gray-50 hover:text-gray-800',
					'group flex cursor-pointer items-center rounded-md px-2 py-1.5 font-medium',
				]"
				@click="currentSidebarItem = item.label"
			>
				<FeatherIcon
					:name="item.icon"
					:class="[
						item.current ? 'text-gray-600' : 'text-gray-500 group-hover:text-gray-600',
						'mr-3 h-4 w-4 flex-shrink-0',
					]"
				/>
				{{ item.label }}
			</div>
		</nav>
	</div>
</template>
