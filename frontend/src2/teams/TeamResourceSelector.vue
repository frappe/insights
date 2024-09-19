<script setup lang="ts">
import { ref } from 'vue'
import { wheneverChanges } from '../helpers'
import useTeamStore, { ResourceOption, Team, TeamPermission } from './teams'

const props = defineProps<{ team: Team }>()
const newResources = defineModel<TeamPermission[]>({
	required: true,
})

const teamStore = useTeamStore()
const groupedResourceOptions = ref([])
const resourceSearchQuery = ref('')
wheneverChanges(
	() => [props.team.name, resourceSearchQuery.value],
	() => {
		if (!props.team.name) return
		teamStore
			.getResourceOptions(props.team.name, resourceSearchQuery.value)
			.then((options: ResourceOption[]) => {
				groupedResourceOptions.value = options.reduce(
					(acc: any, option: ResourceOption) => {
						if (option.resource_type_label === 'Source') {
							acc[0].items.push(option)
						}
						if (option.resource_type_label === 'Table') {
							acc[1].items.push(option)
						}
						return acc
					},
					[
						{ group: 'Data Sources', items: [] },
						{ group: 'Tables', items: [] },
					]
				)
			})
	},
	{ deep: true, debounce: 500, immediate: true }
)
</script>

<template>
	<Autocomplete
		:multiple="true"
		:hide-search="true"
		:autofocus="false"
		v-model="newResources"
		:options="groupedResourceOptions"
	>
		<template #target="{ open }">
			<FormControl
				class="w-full"
				type="text"
				v-model="resourceSearchQuery"
				placeholder="Add permissions"
				autocomplete="off"
				@update:modelValue="open"
				@focus="open"
			/>
		</template>
		<template #footer="{ togglePopover }">
			<div class="flex items-center justify-between p-0.5">
				<p class="px-3 text-sm text-gray-600">
					{{ newResources.length }} resources selected
				</p>
				<div class="flex gap-1">
					<Button
						label="Reset"
						:disabled="!newResources.length"
						@click.prevent.stop="newResources = []"
					>
					</Button>
					<Button
						variant="solid"
						label="Done"
						:disabled="!newResources.length"
						@click="
							() => {
								if (!team) return
								team.team_permissions.push(...newResources)
								newResources = []
								togglePopover(false)
							}
						"
					>
					</Button>
				</div>
			</div>
		</template>
	</Autocomplete>
</template>
