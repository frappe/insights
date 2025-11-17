<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { Dialog } from 'frappe-ui'
import { BubbleChartConfig } from '../../types/chart.types'
import { ColumnOption, Dimension, DimensionOption } from '../../types/query.types'
import DimensionPicker from './DimensionPicker.vue'

type TabType = 'color' | 'labels' | 'reference_lines'

const props = defineProps<{
	dimensions: DimensionOption[]
	columnOptions: ColumnOption[]
	config: BubbleChartConfig
	initialTab?: TabType
}>()

const emit = defineEmits<{
	save: []
}>()

const showDialog = defineModel({ default: false })

const tabs = [
	{ label: 'Color', value: 'color' as TabType },
	{ label: 'Labels', value: 'labels' as TabType },
	{ label: 'Reference Lines', value: 'reference_lines' as TabType },
]
const selectedTab = ref<TabType>(props.initialTab || 'color')

const loadConfig = reactive<BubbleChartConfig>({ ...props.config })
console.log('loadConfig', loadConfig)

watch(() => props.config, (newConfig) => {
	Object.assign(loadConfig, newConfig)
}, { deep: true })

watch(showDialog, (isOpen) => {
	if (isOpen) {
		selectedTab.value = props.initialTab || 'color'
		Object.assign(loadConfig, props.config)
	}
})

function onTabChange(tab: TabType) {
	selectedTab.value = tab
}

function applyChanges() {
	Object.assign(props.config, loadConfig)
	emit('save')
	showDialog.value = false
}

const isChanged = computed(() => {
	return JSON.stringify(props.config) !== JSON.stringify(loadConfig)
})

</script>

<template>
	<Dialog v-model="showDialog" :options="{ size: 'md' }">
		<template #body>
			<div class="min-w-[20rem] rounded-lg bg-white px-4 pb-6 pt-5 sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Chart Options</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md" />
				</div>

				<div class="mb-4 flex gap-1 border-b border-gray-200">
					<button
						v-for="tab in tabs"
						:key="tab.value"
						class="px-4 py-2 text-sm font-medium transition-all"
						:class="
							selectedTab === tab.value
								? 'border-b-2 border-gray-900 text-gray-900'
								: 'text-gray-600 hover:text-gray-900'
						"
						@click="onTabChange(tab.value)"
					>
						{{ tab.label }}
					</button>
				</div>

				<div class="flex flex-col gap-3">
					<div v-if="selectedTab === 'color'" class="flex flex-col gap-3">
						<DimensionPicker
							label="Color by"
							v-model="loadConfig.quadrant_column!"
							:options="props.dimensions"
							@remove="loadConfig.quadrant_column = {} as Dimension"
						/>
						<DimensionPicker
							label="Name Column"
							v-model="loadConfig.dimension!"
							:options="props.dimensions"
							@remove="loadConfig.dimension = {} as Dimension"
						/>
					</div>

					<div v-if="selectedTab === 'labels'" class="flex flex-col gap-3">
						<Toggle
							v-model="loadConfig.show_data_labels"
							label="Show Data Labels"
						/>
					</div>

					<div v-if="selectedTab === 'reference_lines'" class="flex flex-col gap-3">
						<Toggle
							v-model="loadConfig.show_quadrants"
							label="Show Reference Lines"
						/>
						<template v-if="loadConfig.show_quadrants">
							<FormControl
								type="number"
								v-model="loadConfig.xAxis_refLine"
								label="X Axis"
								placeholder="X Axis"
							/>
							<FormControl
								type="number"
								v-model="loadConfig.yAxis_refLine"
								label="Y Axis"
								placeholder="Y Axis"
							/>
						</template>
					</div>
				</div>

				<div class="mt-6 flex items-center justify-end gap-2">
					<Button label="Apply" variant="solid" :disabled="!isChanged" @click="applyChanges" />
				</div>
			</div>
		</template>
	</Dialog>
</template>
