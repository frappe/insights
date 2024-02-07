<script setup>
import { ref, computed, inject } from 'vue'
import ListPicker from '@/components/Controls/ListPicker.vue'

const props = defineProps({
	resourceType: {
		type: String,
		required: true,
	},
})
const resourceTitle = computed(() => props.resourceType.replace('Insights ', ''))
const resourceDescription = computed(() => {
	const description_map = {
		'Insights Data Source':
			'All the tables from these data source will be accessible to the team.',
		'Insights Table':
			'Give access to only specific tables of a data source. Tables from accessible data sources will also be accessible to the team.',
		'Insights Query': 'Queries that are accessible to this team.',
		'Insights Dashboard': 'Dashboards that are accessible to this team.',
	}
	return description_map[props.resourceType]
})

const team = inject('team')
team.searchResources(props.resourceType, '')

const accessibleResources = computed(() => {
	return team.resources?.filter((resource) => resource.type == props.resourceType)
})
const selectedResources = ref([])
const resourceOptions = computed(() => {
	return team.resourceOptions?.map((resource) => {
		const description_map = {
			'Insights Data Source': `${resource.database_type}`,
			'Insights Table': `${resource.data_source}`,
			'Insights Query': `${resource.data_source}`,
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

function addResources(resources) {
	team.addResources(resources)
	selectedResources.value = []
}
</script>

<template>
	<div class="flex w-full flex-col space-y-3 text-base">
		<div class="flex flex-shrink-0 flex-col">
			<div class="text-lg font-medium leading-6">Manage {{ resourceTitle }} Access</div>
			<div class="mb-4 text-sm text-gray-600">
				{{ resourceDescription }}
			</div>
			<ListPicker
				:placeholder="`Add a ${resourceTitle}`"
				v-model="selectedResources"
				:options="resourceOptions"
				:loading="team.search_team_resources.loading"
				@apply="(resources) => addResources(resources)"
				@inputChange="(query) => team.searchResources(props.resourceType, query)"
			></ListPicker>
		</div>

		<div class="flex-1 space-y-3 overflow-y-auto pl-1">
			<div class="divide-y" v-if="accessibleResources && accessibleResources.length">
				<div
					class="flex h-10 items-center justify-between"
					v-for="resource in accessibleResources"
					:key="resource.name"
				>
					<span class="w-[20rem] overflow-hidden text-ellipsis whitespace-nowrap">
						{{ resource.title }}
					</span>
					<div class="flex items-center space-x-2">
						<Button
							icon="x"
							variant="minimal"
							@click="team.removeResource(resource)"
						></Button>
					</div>
				</div>
			</div>
			<div
				v-else
				class="flex h-full items-center justify-center rounded border border-dashed p-4 text-sm font-light text-gray-600"
			>
				No {{ resourceTitle }} added yet.
			</div>
		</div>
	</div>
</template>
