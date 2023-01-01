<template>
	<Dialog :options="{ title: `Manage ${team.doc?.team_name} Team` }" v-model="show">
		<template #body-content>
			<div class="max-h-[70vh] space-y-4 overflow-y-scroll">
				<div class="space-y-3 py-2 text-base">
					<div class="font-medium">Members</div>
					<Autocomplete
						placeholder="Add a member"
						v-model="selectedMember"
						:autofocus="false"
						:options="memberOptions"
						@selectOption="(member) => member && addMember(member)"
						@inputChange="(query) => team.searchMembers(query)"
					></Autocomplete>
					<div class="divide-y text-gray-800" v-if="team.members">
						<div
							class="flex h-12 justify-between px-1"
							v-for="member in team.members"
							:key="member.name"
						>
							<div class="flex items-center space-x-2">
								<Avatar :label="member.full_name" :imageURL="member.image_url" />
								<div>
									<div>{{ member.full_name }}</div>
									<div>{{ member.email }}</div>
								</div>
							</div>
							<div class="flex items-center">
								<Button
									icon="x"
									appearance="minimal"
									@click="team.removeMember(member.name)"
								></Button>
							</div>
						</div>
					</div>
				</div>

				<div class="flex flex-col space-y-3 text-base">
					<div class="font-medium">Manage Data Access</div>
					<div class="space-y-3">
						<Autocomplete
							placeholder="Add a data source or table"
							:options="resourceOptions"
							v-model="selectedResource"
							@inputChange="(query) => team.searchResources(query)"
							@selectOption="(resource) => resource && addResource(resource)"
						></Autocomplete>
						<div class="divide-y" v-if="team.resources">
							<div
								class="flex h-10 cursor-pointer items-center justify-between rounded-md px-2 hover:bg-gray-50"
								v-for="resource in team.resources"
								:key="resource.name"
							>
								<span
									class="w-[20rem] overflow-hidden text-ellipsis whitespace-nowrap"
								>
									{{ resource.title }}
								</span>
								<div class="flex items-center space-x-4">
									<div class="text-gray-500">
										{{ resource.type.replace('Insights ', '') }}
									</div>
									<Button
										icon="x"
										appearance="minimal"
										@click="team.removeResource(resource)"
									></Button>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
		<template #actions>
			<div class="flex justify-end space-x-2">
				<Button appearance="secondary" @click="emit('close')">Close</Button>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useTeam } from '@/utils/useTeams.js'
import Autocomplete from '@/components/Controls/Autocomplete.vue'

const emit = defineEmits(['close'])
const props = defineProps({
	teamname: {
		type: String,
		required: true,
	},
})

const team = useTeam(props.teamname)
const show = computed({
	get: () => Boolean(team.doc?.team_name),
	set: (value) => {
		if (!value) {
			emit('close')
		}
	},
})

const selectedMember = ref(null)
const memberOptions = computed(() => {
	return team.memberOptions?.map((member) => {
		return {
			label: member.full_name,
			description: member.email,
			value: member.name,
		}
	})
})
function addMember(member) {
	team.addMember(member.value)
	selectedMember.value = null
}

const selectedResource = ref(null)
const resourceOptions = computed(() => {
	return team.resourceOptions?.map((resource) => {
		const description_map = {
			'Insights Data Source': `${resource.database_type} - Data Source`,
			'Insights Table': `${resource.data_source} - Table`,
			'Insights Query': `${resource.data_source} - Query`,
			'Insights Dashboard': '',
		}
		return {
			...resource,
			value: resource.name,
			label: resource.title,
			description: description_map[resource.type],
		}
	})
})

function addResource(resource) {
	team.addResource(resource)
	selectedResource.value = null
}
</script>
