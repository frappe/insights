<script setup lang="ts">
import { Edit, Plus, Settings, XIcon } from 'lucide-vue-next'
import { computed, inject, ref } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { Query } from '../../query/query'
import { ExpressionMeasure, Measure, aggregations } from '../../types/query.types'
import { Chart } from '../chart'
import { MeasureOption } from './ChartConfigForm.vue'
import NewMeasureSelectorDialog from './NewMeasureSelectorDialog.vue'

const emit = defineEmits({ remove: () => true })
const props = defineProps<{
	label?: string
	options: MeasureOption[]
}>()

const measure = defineModel<Measure>({
	required: true,
	default: () => {
		return {
			column_name: '',
			data_type: 'String',
			measure_name: '',
			aggregation: 'sum',
		}
	},
})

function selectMeasure(option?: MeasureOption) {
	if (!option || !option.measure_name) {
		measure.value = {
			column_name: '',
			data_type: 'String',
			measure_name: '',
			aggregation: 'sum',
		}
		return
	}
	measure.value = option
}

const query = inject<Query>('query')!
const chart = inject<Chart>('chart')!

const queryColumns = computed(() => {
	if (query) return query.result.columnOptions
	if (chart) return chart.baseQuery.result.columnOptions
	return []
})

const showMeasureDialog = ref(false)
const isExpressionMeasure = computed(
	() => 'expression' in measure.value && measure.value.expression.expression
)
function updateMeasure(measureExpression: ExpressionMeasure) {
	measure.value = measureExpression
	showMeasureDialog.value = false
}
</script>

<template>
	<div class="flex items-end gap-1 overflow-hidden">
		<div class="flex-1 overflow-hidden">
			<Autocomplete
				:label="props.label"
				placeholder="Select a column"
				:showFooter="true"
				:options="props.options"
				:modelValue="measure.measure_name"
				@update:modelValue="selectMeasure"
			>
				<template #footer="{ togglePopover }">
					<Button
						class="w-full"
						variant="ghost"
						:label="isExpressionMeasure ? 'Edit Measure' : 'New Measure'"
						@click=";(showMeasureDialog = true), togglePopover()"
					>
						<template #prefix>
							<component
								:is="isExpressionMeasure ? Edit : Plus"
								class="h-4 w-4 text-gray-700"
								stroke-width="1.5"
							/>
						</template>
					</Button>
				</template>
			</Autocomplete>
		</div>
		<Popover v-if="measure.measure_name" placement="bottom-end">
			<template #target="{ togglePopover }">
				<Button @click="togglePopover">
					<template #icon>
						<Settings class="h-4 w-4 text-gray-700" stroke-width="1.5" />
					</template>
				</Button>
			</template>
			<template #body-main>
				<div class="flex w-[14rem] flex-col gap-2 p-2">
					<InlineFormControlLabel
						v-if="
							'aggregation' in measure &&
							measure.aggregation &&
							measure.column_name != 'count'
						"
						label="Function"
					>
						<Autocomplete
							placeholder="Agg"
							:options="aggregations"
							:modelValue="measure.aggregation"
							@update:modelValue="measure.aggregation = $event.value"
							:hide-search="true"
						/>
					</InlineFormControlLabel>

					<InlineFormControlLabel label="Label">
						<FormControl
							v-model="measure.measure_name"
							autocomplete="off"
							:debounce="500"
						/>
					</InlineFormControlLabel>

					<slot name="config-fields" />

					<div class="flex gap-1">
						<Button class="w-full" @click="emit('remove')" theme="red">
							<template #prefix>
								<XIcon class="h-4 w-4 text-red-700" stroke-width="1.5" />
							</template>
							Remove
						</Button>
					</div>
				</div>
			</template>
		</Popover>
		<Button v-else @click="emit('remove')">
			<template #icon>
				<XIcon class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
		</Button>
	</div>

	<NewMeasureSelectorDialog
		v-if="showMeasureDialog"
		:model-value="Boolean(showMeasureDialog)"
		@update:model-value="!$event && (showMeasureDialog = false)"
		:column-options="queryColumns"
		:measure="(measure as ExpressionMeasure)"
		@select="updateMeasure"
	/>
</template>
