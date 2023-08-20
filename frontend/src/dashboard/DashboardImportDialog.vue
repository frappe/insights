<script setup>
import useDashboards from '@/dashboard/useDashboards'
import useDataSourceStore from '@/stores/dataSourceStore'
import { FileUploader } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const emit = defineEmits(['update:show'])
const props = defineProps({ show: Boolean })

const show = computed({
	get: () => props.show,
	set: (value) => emit('update:show', value),
})

const dataSourceStore = useDataSourceStore()

const dashboards = useDashboards()
const dashboardFile = ref(null)
const dashboardDataSources = ref([])
watch(dashboardFile, async () => {
	if (!dashboardFile.value) return
	const dashboard = await dashboards.getDashboardFile(dashboardFile.value.name)
	dashboardDataSources.value = dashboard.data_sources
})
const newDashboardTitle = ref('')
const dataSourceMap = ref({})
const importDisabled = computed(() => {
	return (
		!dashboardFile ||
		!dashboardFile.value ||
		!newDashboardTitle.value ||
		!dashboardDataSources ||
		!dashboardDataSources.value.length ||
		!Object.keys(dataSourceMap.value).length ||
		!Object.values(dataSourceMap.value).every((d) => d)
	)
})
function importDashboard() {
	dashboards.import({
		file: dashboardFile.value,
		title: newDashboardTitle.value,
		dataSourceMap: dataSourceMap.value,
	})
	show.value = false
}
</script>

<template>
	<Dialog :options="{ title: 'Import Dashboard' }" v-model="show">
		<template #body-content>
			<div v-if="!dashboardFile">
				<FileUploader @success="(file) => (dashboardFile = file)">
					<template #default="{ progress, uploading, openFileSelector }">
						<div
							class="flex cursor-pointer flex-col items-center justify-center rounded border border-dashed border-gray-300 p-8 text-base"
							@click="openFileSelector"
						>
							<FeatherIcon name="file" class="h-8 w-8 text-gray-500" />
							<div class="mt-2 text-gray-600">
								<p v-if="!uploading" class="text-center font-medium text-blue-500">
									Select a file
								</p>
								<p v-else class="text-center font-medium text-blue-500">
									Uploading... ({{ progress }}%)
								</p>
								<p
									v-if="!uploading && !dashboardFile"
									class="mt-1 text-center text-xs"
								>
									JSON files upto 10MB
								</p>
							</div>
						</div>
					</template>
				</FileUploader>
			</div>

			<div v-else class="flex flex-col">
				<div class="mb-6 flex flex-1 flex-col space-y-3">
					<Input
						label="New Dashboard Title"
						type="text"
						placeholder="eg. Sales Dashboard"
						v-model="newDashboardTitle"
					/>
				</div>
				<div v-if="dashboardDataSources?.length" class="mb-3">
					<p class="text-lg font-medium leading-6 text-gray-900">Data Source Mapping</p>
					<p class="text-sm text-gray-500">
						Select the data source for each data source in the dashboard
					</p>
				</div>
				<div
					v-if="dashboardDataSources?.length"
					class="flex max-h-[15rem] flex-col overflow-hidden text-base"
				>
					<div class="flex flex-col overflow-y-scroll">
						<div
							v-for="dataSource in dashboardDataSources"
							class="flex h-10 w-full cursor-pointer items-center space-x-8 text-gray-600"
						>
							<span
								class="flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium"
							>
								{{ dataSource }}
							</span>
							<Input
								class="flex-1 !text-sm"
								type="select"
								v-model="dataSourceMap[dataSource]"
								:options="
									[{ label: 'Select Data Source', value: '' }].concat(
										dataSourceStore.dropdownOptions
									)
								"
							/>
						</div>
					</div>
				</div>
			</div>
		</template>
		<template #actions>
			<Button
				class="w-full"
				variant="solid"
				:disabled="importDisabled"
				:loading="dashboards.creating"
				@click="importDashboard"
			>
				Import
			</Button>
		</template>
	</Dialog>
</template>
