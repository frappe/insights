<template>
	<Dialog :options="{ title: `Manage ${team.doc?.team_name} Team`, size: '3xl' }" v-model="show">
		<template #body>
			<div class="flex h-[70vh] text-base">
				<ManageTeamSidebar
					@change="currentSidebarItem = $event"
					@delete-team="show = false"
				></ManageTeamSidebar>
				<div class="flex w-3/4 space-y-4 overflow-y-auto p-5">
					<ManageTeamMembers v-if="currentSidebarItem == 'Members'" />
					<ManageTeamResourceAccess
						v-if="currentSidebarItem != 'Members'"
						:key="currentSidebarItem"
						:resourceType="
							{
								'Data Sources': 'Insights Data Source',
								Tables: 'Insights Table',
								Queries: 'Insights Query',
								Dashboards: 'Insights Dashboard',
							}[currentSidebarItem]
						"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed, provide } from 'vue'
import { useTeam } from '@/utils/useTeams.js'
import ManageTeamSidebar from './ManageTeamSidebar.vue'
import ManageTeamMembers from './ManageTeamMembers.vue'
import ManageTeamResourceAccess from './ManageTeamResourceAccess.vue'

const emit = defineEmits(['close'])
const props = defineProps({
	teamname: {
		type: String,
		required: true,
	},
})

const currentSidebarItem = ref('Members')
const team = useTeam(props.teamname)
provide('team', team)
const show = computed({
	get: () => Boolean(team.doc?.team_name),
	set: (value) => {
		if (!value) {
			emit('close')
		}
	},
})
</script>
