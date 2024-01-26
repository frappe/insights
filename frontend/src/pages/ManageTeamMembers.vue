<script setup>
import { ref, computed, inject } from 'vue'
import ListPicker from '@/components/Controls/ListPicker.vue'

const team = inject('team')
const selectedMembers = ref([])
const memberOptions = computed(() => {
	return team.memberOptions?.map((member) => {
		return {
			label: member.full_name,
			description: member.email,
			value: member.name,
		}
	})
})
const addingMember = ref(false)
function addMembers(members) {
	addingMember.value = true
	team.addMembers(members.map((member) => member.value))
		.then(() => {
			addingMember.value = false
		})
		.catch(() => {
			addingMember.value = false
		})
	selectedMembers.value = []
}
</script>

<template>
	<div class="flex w-full flex-col space-y-3 text-base">
		<div class="flex flex-shrink-0 flex-col space-y-2">
			<div class="text-lg font-medium">Members</div>
			<ListPicker
				placeholder="Add a member"
				v-model="selectedMembers"
				:options="memberOptions"
				:loading="team.search_team_members.loading"
				@inputChange="(query) => team.searchMembers(query)"
				@apply="(selected) => addMembers(selected)"
			></ListPicker>
		</div>
		<div
			class="flex-1 divide-y overflow-y-auto text-gray-800"
			v-if="team.members && team.members.length"
		>
			<div
				class="flex h-12 justify-between px-1"
				v-for="member in team.members"
				:key="member.name"
			>
				<div class="flex items-center space-x-2">
					<Avatar :label="member.full_name" :image="member.user_image" />
					<div>
						<div>{{ member.full_name }}</div>
						<div class="text-sm text-gray-600">{{ member.email }}</div>
					</div>
				</div>
				<div class="flex items-center">
					<Button
						icon="x"
						variant="minimal"
						@click="team.removeMember(member.name)"
					></Button>
				</div>
			</div>
		</div>
		<div v-else-if="addingMember" class="flex flex-1 items-center justify-center text-gray-500">
			<LoadingIndicator class="h-6 w-6" />
		</div>
		<div
			v-else
			class="flex flex-1 items-center justify-center rounded border border-dashed p-4 font-light text-gray-500"
		>
			This team has no members
		</div>
	</div>
</template>
