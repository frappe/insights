<template>
	<Dialog :options="{ title: 'Share' }" v-model="show" :dismissable="true">
		<template #body-content>
			<div class="space-y-4 text-base">
				<Autocomplete
					:options="unauthorizedTeams"
					placeholder="Search for a team..."
					@selectOption="handleAccessGrant"
					v-model="newUser"
				/>
				<div class="space-y-3">
					<div class="text-gray-600">Teams with access</div>
					<div class="space-y-3">
						<div
							class="flex items-center text-gray-600"
							v-for="team in authorizedTeams"
							:key="team.name"
						>
							<Avatar :label="team.team_name" />
							<div class="ml-2 flex flex-col">
								<span>{{ team.team_name }}</span>
								<span class="text-gray-400">{{ team.members_count }} members</span>
							</div>
							<Button
								icon="x"
								class="ml-auto"
								@click="handleAccessRevoke(team.name)"
							></Button>
						</div>
					</div>
				</div>
			</div>
		</template>
		<template #actions>
			<Button appearance="primary" @click="show = false"> Done </Button>
		</template>
	</Dialog>
</template>

<script setup>
import Autocomplete from '@/components/controls/Autocomplete.vue'
import { computed, watch, ref } from 'vue'
import { createResource } from 'frappe-ui'

const emit = defineEmits(['update:show'])
const props = defineProps({
	show: {
		type: Boolean,
		required: true,
	},
	resourceType: {
		type: String,
		required: true,
	},
	resourceName: {
		type: String,
		required: true,
	},
})

const show = computed({
	get: () => props.show,
	set: (value) => {
		emit('update:show', value)
	},
})

const getAccessInfo = createResource({
	url: 'insights.api.permissions.get_resource_access_info',
	params: {
		resource_type: props.resourceType,
		resource_name: props.resourceName,
	},
})
watch(show, (newVal, oldVal) => {
	if (newVal && !oldVal) {
		getAccessInfo.fetch()
	}
})

const authorizedTeams = computed(() => {
	return getAccessInfo.data?.authorized_teams
})

const newUser = ref(null)
const unauthorizedTeams = computed(() => {
	return getAccessInfo.data?.unauthorized_teams.map((team) => {
		return {
			label: team.team_name,
			value: team.name,
			description: team.members_count + ' members',
		}
	})
})

const grantAccess = createResource({
	url: 'insights.api.permissions.grant_access',
})
function handleAccessGrant(team) {
	grantAccess.submit({
		resource_type: props.resourceType,
		resource_name: props.resourceName,
		team: team.value,
	})
	getAccessInfo.fetch()
	newUser.value = null
}

const revokeAccess = createResource({
	url: 'insights.api.permissions.revoke_access',
})
function handleAccessRevoke(team) {
	revokeAccess.submit({
		resource_type: props.resourceType,
		resource_name: props.resourceName,
		team: team,
	})
	getAccessInfo.fetch()
}
</script>
