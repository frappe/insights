<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { call } from 'frappe-ui'
import { Dialog, Button, Autocomplete, LoadingIndicator, TextInput } from 'frappe-ui'
import { MappingData, Region } from '../../types/chart.types'
import { Trash2Icon } from 'lucide-vue-next'
const props = defineProps<{
	modelValue: boolean
	chartName: string
	mapType: string
	userRegions: string[]
}>()

const emit = defineEmits<{
	'update:modelValue': [value: boolean]
	mappingsSaved: []
}>()

const loading = ref(false)
const saving = ref(false)
const data = ref<MappingData | null>(null)
const localMappings = ref<Record<string, string>>({})
const searchQuery = ref('')

watch(
	() => props.modelValue,
	async (open) => {
		if (open) await loadData()
	},
	{ immediate: true }
)

async function loadData() {
	if (!props.userRegions?.length) return

	loading.value = true
	try {
		const [mappingResponse, regionsResponse] = await Promise.all([
			call('insights.api.maps.find_unresolved_regions', {
				map_type: props.mapType,
				user_regions: props.userRegions,
				chart_name: props.chartName,
			}),
			call('insights.api.maps.get_available_regions', {
				map_type: props.mapType,
			}),
		])

		// Extract manual mappings
		const manualMappings: Record<string, string> = {}
		mappingResponse.resolved?.forEach((region: any) => {
			if (region.method === 'manual_mapping') {
				manualMappings[region.user_region] = region.mapped_to
			}
		})

		data.value = {
			total: mappingResponse.total_regions,
			resolved: mappingResponse.resolved_count,
			unresolved: mappingResponse.unresolved_count,
			unresolved_list: mappingResponse.unresolved || [],
			manual_mappings: manualMappings,
			available_regions: regionsResponse.regions || [],
		}

		localMappings.value = { ...manualMappings }
	} catch (error) {
		console.error('Failed to load mapping data:', error)
	} finally {
		loading.value = false
	}
}

async function save() {
	if (!hasChanges.value) return

	saving.value = true
	try {
		const changes: Record<string, string> = {}

		// Add new/updated mappings
		Object.entries(localMappings.value).forEach(([region, mapped]) => {
			changes[region] = mapped
		})

		// Mark removed mappings
		Object.keys(data.value?.manual_mappings || {}).forEach((region) => {
			if (!localMappings.value[region]) {
				changes[region] = ''
			}
		})

		await call('insights.api.maps.save_region_mappings', {
			chart_name: props.chartName,
			map_type: props.mapType,
			mappings: changes,
		})

		emit('mappingsSaved')
		await loadData()
	} catch (error) {
		console.error('Failed to save mappings:', error)
	} finally {
		saving.value = false
	}
}

function updateMapping(region: string, value: any) {
	const mapped = typeof value === 'string' ? value : value?.value || ''
	if (mapped) {
		localMappings.value[region] = mapped
	} else {
		delete localMappings.value[region]
	}
}

function removeMapping(region: string) {
	delete localMappings.value[region]
}

const hasChanges = computed(() => {
	const original = data.value?.manual_mappings || {}
	const current = localMappings.value

	if (Object.keys(original).length !== Object.keys(current).length) return true

	return Object.entries(current).some(([region, mapped]) => original[region] !== mapped)
})

const unresolvedRegions = computed(() => {
	if (!data.value) return []

	const regions: Region[] = []

	// Add backend unresolved regions that aren't locally mapped
	data.value.unresolved_list.forEach((region) => {
		if (!localMappings.value[region.user_region]) {
			regions.push(region)
		}
	})

	// Add removed manual mappings back to unresolved
	Object.keys(data.value.manual_mappings).forEach((region) => {
		if (!localMappings.value[region] && !regions.find((r) => r.user_region === region)) {
			regions.push({ user_region: region, suggestions: [] })
		}
	})

	const filteredRegions = regions.filter((region) =>
		region.user_region.toLowerCase().includes(searchQuery.value.toLowerCase())
	)
	return filteredRegions
})

const manualMappings = computed(() => {
	return Object.entries(localMappings.value).map(([user_region, mapped_to]) => ({
		user_region,
		mapped_to,
	}))
})

const usedRegions = computed(() => new Set(Object.values(localMappings.value)))

function getOptions(region: Region) {
	const available = data.value?.available_regions || []
	const options: Array<{ label: string; value: string }> = []

	// Add suggestions first
	region.suggestions?.forEach((s) => {
		if (!usedRegions.value.has(s.region)) {
			options.push({
				label: `${s.region} (${Math.round(s.similarity * 100)}% match)`,
				value: s.region,
			})
		}
	})

	// Add remaining available regions
	const suggested = new Set(region.suggestions?.map((s) => s.region) || [])
	available.forEach((r) => {
		if (!suggested.has(r) && !usedRegions.value.has(r)) {
			options.push({ label: r, value: r })
		}
	})

	return options
}
</script>

<template>
	<Dialog
		:modelValue="modelValue"
		:options="{ title: 'Resolve Locations', size: '2xl' }"
		@update:modelValue="emit('update:modelValue', $event)"
	>
		<template #body-content>
			<!-- Loading State -->
			<div v-if="loading" class="flex h-[28rem] items-center justify-center">
				<div class="flex flex-col items-center gap-3">
					<LoadingIndicator class="h-5 w-5 text-gray-400" />
					<span class="text-sm text-gray-500">Loading</span>
				</div>
			</div>

			<div v-else-if="data" class="flex h-[28rem] flex-col gap-6">
				<!-- Scrollable Content Area -->
				<div class="flex min-h-0 flex-1 flex-col gap-4">
					<!-- Unresolved Regions -->
					<div class="flex flex-col">
						<div class="mb-2 flex items-center gap-2">
							<h3 class="text-sm font-medium text-gray-700">
								{{ unresolvedRegions.length }}
							</h3>
							<h3 class="text-sm font-bold text-gray-900">Unresolved Locations</h3>
						</div>
						<div class="h-[15rem] overflow-y-auto rounded-md border bg-white">
							<TextInput
								v-model="searchQuery"
								placeholder="Search locations"
								class="w-1/3 p-2"
								variant="subtle"
							/>
							<div class="flex flex-col divide-y">
								<div
									v-for="region in unresolvedRegions"
									:key="region.user_region"
									class="group flex items-center gap-3 px-3 py-2 hover:bg-gray-50/60"
								>
									<p class="min-w-0 flex-1 truncate text-sm text-gray-900">
										{{ region.user_region }}
									</p>

									<div class="w-56 flex-shrink-0">
										<Autocomplete
											placeholder="Select region..."
											:modelValue="localMappings[region.user_region] || ''"
											@update:modelValue="
												updateMapping(region.user_region, $event)
											"
											:options="getOptions(region)"
										/>
									</div>
								</div>
							</div>
						</div>
					</div>

					<!-- Resolved Regions -->
					<div class="flex flex-col">
						<div class="mb-2 flex items-center gap-2">
							<h3 class="text-sm font-medium text-gray-700">
								{{ manualMappings.length }}
							</h3>
							<h3 class="text-sm font-medium text-gray-900">Resolved</h3>
						</div>

						<div class="h-[10rem] overflow-y-auto rounded-md border bg-white">
							<div class="flex flex-col divide-y h-full">
								<div
									v-if="manualMappings.length === 0"
									class="flex items-center justify-center flex-1 text-sm text-gray-500"
								>
									No Locations Resolved
								</div>
								<div
									v-for="mapping in manualMappings"
									:key="mapping.user_region"
									class="group flex items-center gap-3 px-3 py-2 hover:bg-gray-50/60"
								>
									<p class="min-w-0 flex-1 truncate text-sm text-gray-600">
										{{ mapping.user_region }}
									</p>

									<div class="w-56 flex-shrink-0">
										<Autocomplete
											:modelValue="mapping.mapped_to"
											@update:modelValue="
												updateMapping(mapping.user_region, $event)
											"
											:options="
												getOptions({
													user_region: mapping.user_region,
													suggestions: [],
												})
											"
											placeholder="Select region..."
										/>
									</div>

									<Button
										variant="icon"
										@click="removeMapping(mapping.user_region)"
										class="text-red-600"
										:icon="Trash2Icon"
									>
									</Button>
								</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex justify-end gap-2">
				<Button label="Cancel" @click="emit('update:modelValue', false)" />
				<Button
					label="Save Changes"
					variant="solid"
					:loading="saving"
					:disabled="!hasChanges"
					@click="save"
				/>
			</div>
		</template>
	</Dialog>
</template>
