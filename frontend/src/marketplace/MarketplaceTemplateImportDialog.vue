<script setup>
import useDataSourceStore from '@/stores/dataSourceStore'
import useMarketplaceStore from '@/stores/marketplaceStore'
import widgets from '@/widgets/widgets'
import { Download } from 'lucide-vue-next'
import { computed, inject, ref, watch } from 'vue'

const dataSourceStore = useDataSourceStore()
const marketplaceStore = useMarketplaceStore()
const template = computed(() => marketplaceStore.importDialogTemplate)

const newDashboardTitle = ref('')

const dataSourceMap = ref({})
watch(template, () => {
	if (!template.value) {
		newDashboardTitle.value = ''
		dataSourceMap.value = {}
		return
	}
	newDashboardTitle.value = template.value.title
	template.value.charts.forEach((chart) => {
		dataSourceMap.value[chart.data_source] = ''
	})
})

const dataSourceOptions = computed(() => {
	const placeholder = { label: 'Select Data Source', value: '' }
	return [placeholder, ...dataSourceStore.dropdownOptions]
})

const importDisabled = computed(() => {
	return !newDashboardTitle.value || !Object.values(dataSourceMap.value).every(Boolean)
})

const $notify = inject('$notify')
async function handleImport() {
	// await marketplaceStore.importTemplate(
	// 	template.value,
	// 	newDashboardTitle.value,
	// 	dataSourceMap.value
	// )
	$notify({
		title: 'Template Imported',
		message: `Template ${template.value.title} imported successfully`,
		variant: 'success',
	})
	marketplaceStore.closeImportDialog()
}
</script>

<template>
	<Dialog
		v-model="marketplaceStore.importDialogOpen"
		:dismissable="true"
		:options="{ title: 'Import Template' }"
	>
		<template #body-content>
			<div class="text-base">
				<div class="-mt-4 text-sm text-gray-600">
					Importing this template will create a new dashboard and new queries for each
					chart
				</div>
				<div class="mt-4">
					<Input
						type="text"
						v-model="newDashboardTitle"
						label="Dashboard Title"
						placeholder="Enter a title for the new dashboard"
					/>
				</div>
				<div v-if="template" class="mt-4">
					<p class="font-bold leading-6 text-gray-900">Map Data Sources</p>
					<p class="text-sm text-gray-600">
						Map the data sources used in this template to your existing data sources
					</p>
					<div class="mt-3 flex max-h-[15rem] flex-col overflow-hidden text-base">
						<div class="flex flex-col space-y-2 overflow-y-scroll pr-1">
							<div
								v-for="chart in template.charts"
								class="flex h-10 w-full cursor-pointer items-center space-x-8"
							>
								<div
									class="flex flex-1 flex-shrink-0 items-center space-x-2 overflow-hidden"
								>
									<component
										v-if="widgets[chart.type]"
										:is="widgets[chart.type].icon"
										class="h-4 w-4 text-gray-600"
									/>
									<span
										class="flex-1 overflow-hidden text-ellipsis whitespace-nowrap text-base font-medium"
									>
										{{ chart.title }}
									</span>
								</div>
								<div class="flex-1 flex-shrink-0">
									<Input
										class="w-full !text-xs"
										type="select"
										:options="dataSourceOptions"
										:modelValue="dataSourceMap[chart.data_source]"
										@update:modelValue="
											dataSourceMap[chart.data_source] = $event
										"
									/>
								</div>
							</div>
						</div>
					</div>
				</div>

				<div class="mt-6 flex justify-end">
					<Button variant="solid" @click="handleImport" :disabled="importDisabled">
						<template #prefix>
							<Download class="h-4 w-4" />
						</template>
						<span>Import</span>
					</Button>
				</div>
			</div>
		</template>
	</Dialog>
</template>
