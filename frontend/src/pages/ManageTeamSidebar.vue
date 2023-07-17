<script setup>
import { showPrompt } from '@/utils/prompt'
import { ref, computed, inject } from 'vue'

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
	{
		label: 'Delete Team',
		icon: 'trash-2',
		variant: 'solid',
		theme: 'red',
	},
])
const emit = defineEmits(['change', 'delete-team'])
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

const team = inject('team')
function handleSidebarItemClick(item) {
	if (item.variant == 'danger') {
		showDeletePrompt()
	} else {
		currentSidebarItem.value = item.label
	}
}

function showDeletePrompt() {
	showPrompt({
		title: 'Delete Team',
		message: `Are you sure you want to delete this team?`,
		icon: { name: 'trash', variant: 'solid', theme: 'red' },
		primaryAction: {
			label: 'Delete',
			variant: 'solid',
			theme: 'red',
			action: ({ close }) => {
				return team
					.deleteTeam()
					.then(close)
					.then(() => emit('delete-team'))
			},
		},
	})
}
</script>
<template>
	<div class="w-1/4 bg-gray-50 p-3 text-gray-600">
		<div class="mb-2 text-lg font-medium text-gray-800">{{ team.doc.team_name }} Team</div>
		<nav class="flex-1 space-y-1 pb-4 text-base">
			<div
				v-for="item in sidebarItems"
				:key="item.label"
				:class="[
					item.current ? 'bg-gray-200/70' : 'text-gray-600 ',
					item.variant == 'danger'
						? 'text-red-600 hover:bg-gray-200/70 hover:text-red-600'
						: 'text-gray-600 hover:bg-gray-200/70 hover:text-gray-800',
					'group flex cursor-pointer items-center rounded px-2 py-1.5 font-medium hover:bg-gray-200/70 hover:text-gray-800',
				]"
				@click="handleSidebarItemClick(item)"
			>
				<FeatherIcon :name="item.icon" :class="['mr-3 h-4 w-4 flex-shrink-0']" />
				{{ item.label }}
			</div>
		</nav>
	</div>
</template>
