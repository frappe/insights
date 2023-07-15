<template>
	<Dialog :options="{ title: 'Add Team' }" v-model="show">
		<template #body-content>
			<Form
				v-model="newTeam"
				:meta="{
					fields: [
						{
							name: 'team_name',
							label: 'Team Name',
							type: 'text',
							placeholder: 'Enter team name',
						},
					],
				}"
			/>
		</template>
		<template #actions>
			<Button variant="solid" :disabled="!newTeam.team_name" @click="addTeam"> Add </Button>
			<Button @click="show = false">Cancel</Button>
		</template>
	</Dialog>
</template>

<script setup>
import { reactive, computed } from 'vue'
import { createResource } from 'frappe-ui'
import { useTeams } from '@/utils/useTeams'
import Form from './Form.vue'

const emit = defineEmits(['close'])
const show = computed({
	get: () => true,
	set: (value) => {
		if (!value) {
			emit('close')
		}
	},
})
const newTeam = reactive({
	team_name: '',
})

const teams = useTeams()
const addTeamResource = createResource({
	url: 'insights.insights.doctype.insights_team.insights_team_client.add_new_team',
})

function addTeam() {
	addTeamResource
		.submit({
			team_name: newTeam.team_name,
		})
		.then(() => {
			teams.refresh()
			emit('close')
		})
}
</script>
