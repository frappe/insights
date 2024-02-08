<template>
	<BasePage>
		<template #header>
			<div class="flex flex-1 justify-between">
				<h1 class="text-3xl font-medium text-gray-900">Teams</h1>
				<div class="space-x-4">
					<Button
						variant="outline"
						class="shadow"
						iconLeft="plus"
						@click="showAddTeamDialog = true"
						>Add Team</Button
					>
				</div>
			</div>
		</template>
		<template #main>
			<div class="flex flex-1 flex-col overflow-hidden">
				<div class="mb-4 flex flex-shrink-0 space-x-4">
					<Input type="text" placeholder="Team Name" />
				</div>
				<div class="flex flex-1 flex-col rounded border">
					<!-- List Header -->
					<div
						class="flex flex-shrink-0 items-center justify-between border-b px-4 py-3 text-sm text-gray-600"
					>
						<p class="mr-4">
							<Input type="checkbox" class="rounded border-gray-300" />
						</p>
						<p class="flex-1 flex-shrink-0">Team Name</p>
						<p class="flex-1 flex-shrink-0">Members</p>
						<p class="hidden flex-1 flex-shrink-0 lg:inline-block">Data Sources</p>
						<p class="hidden flex-1 flex-shrink-0 lg:inline-block">Tables</p>
						<p class="hidden flex-1 flex-shrink-0 lg:inline-block">Queries</p>
						<p class="hidden flex-1 flex-shrink-0 lg:inline-block">Dashboards</p>
					</div>
					<ul
						role="list"
						v-if="teams.list?.length > 0"
						class="flex flex-1 flex-col divide-y divide-gray-200 overflow-y-auto"
					>
						<li
							v-for="team in teams.list"
							:key="team.name"
							@click="teamToEdit = team.name"
						>
							<div
								class="flex h-11 cursor-pointer items-center rounded px-4 hover:bg-gray-50"
							>
								<p class="mr-4">
									<Input type="checkbox" class="rounded border-gray-300" />
								</p>
								<p
									class="flex-1 flex-shrink-0 overflow-hidden text-ellipsis whitespace-nowrap text-sm font-medium text-gray-900"
								>
									{{ team.team_name }}
								</p>
								<p
									class="flex-1 flex-shrink-0 overflow-hidden whitespace-nowrap text-sm text-gray-600"
								>
									<Avatars
										v-if="team.members.length > 0"
										:avatars="getAvatars(team.members)"
									></Avatars>
									<span v-else> - </span>
								</p>
								<p
									class="hidden flex-1 flex-shrink-0 overflow-hidden whitespace-nowrap text-sm text-gray-600 lg:inline-block"
								>
									{{ team.source_count }}
								</p>
								<p
									class="hidden flex-1 flex-shrink-0 overflow-hidden whitespace-nowrap text-sm text-gray-600 lg:inline-block"
								>
									{{ team.table_count }}
								</p>
								<p
									class="hidden flex-1 flex-shrink-0 overflow-hidden whitespace-nowrap text-sm text-gray-600 lg:inline-block"
								>
									{{ team.query_count }}
								</p>
								<p
									class="hidden flex-1 flex-shrink-0 overflow-hidden whitespace-nowrap text-sm text-gray-600 lg:inline-block"
								>
									{{ team.dashboard_count }}
								</p>
							</div>
						</li>
					</ul>
				</div>
			</div>
		</template>
	</BasePage>

	<AddTeamDialog v-if="showAddTeamDialog" @close="showAddTeamDialog = false"></AddTeamDialog>

	<ManageTeamDialog
		v-if="teamToEdit"
		:teamname="teamToEdit"
		@close="teamToEdit = null"
	></ManageTeamDialog>
</template>

<script setup>
import { ref } from 'vue'
import BasePage from '@/components/BasePage.vue'
import { useTeams } from '@/utils/useTeams.js'
import ManageTeamDialog from './ManageTeamDialog.vue'
import AddTeamDialog from './AddTeamDialog.vue'
import Avatars from './Avatars.vue'

const teams = useTeams()
const teamToEdit = ref(null)
const showAddTeamDialog = ref(false)

function getAvatars(members) {
	return members
		.map((member) => ({
			label: member.full_name,
			image: member.user_image,
		}))
		.slice(0, 3)
		.concat(members.length > 3 ? [{ label: `${members.length - 3}` }] : [])
}
</script>
