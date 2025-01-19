<script setup lang="ts">
import { computed, reactive } from 'vue'
import { copy } from '../helpers'
import { FilterType } from '../helpers/constants'
import ColumnFilterValueSelector from '../query/components/ColumnFilterValueSelector.vue'
import DatePicker from '../query/components/DatePicker.vue'
import { getOperatorOptions, getValueSelectorType } from '../query/components/filter_utils'
import NumberFilterPicker from '../query/components/NumberFilterPicker.vue'
import RelativeDatePicker from '../query/components/RelativeDatePicker.vue'
import { FilterOperator, FilterValue } from '../types/query.types'

const props = defineProps<{
	filterType: FilterType
	valuesProvider: (search: string) => Promise<string[]>
}>()
const filterOperator = defineModel<FilterOperator>('operator')
const filterValue = defineModel<FilterValue>('value')

const operatorOptions = computed(() => {
	return getOperatorOptions(props.filterType)
})

const state = reactive(
	copy({
		operator: filterOperator.value || operatorOptions.value[0].value,
		value: filterValue.value,
	})
)

const valueSelectorType = computed(() => {
	if (!state.operator) return
	return getValueSelectorType(state.operator, props.filterType)
})

function onOperatorChange(operator: FilterOperator) {
	const oldValueSelectorType = valueSelectorType.value
	state.operator = operator
	if (oldValueSelectorType !== valueSelectorType.value) {
		state.value = undefined
	}
}

function applyFilter() {
	filterOperator.value = state.operator
	filterValue.value = state.value
}
function clearFilter() {
	filterOperator.value = undefined
	filterValue.value = undefined
}
</script>

<template>
	<div class="flex flex-col gap-2">
		<NumberFilterPicker
			v-if="filterType === 'Number'"
			class="w-[200px]"
			v-model:operator="state.operator"
			v-model:value="(state.value as number)"
		/>
		<template v-else>
			<div id="operator" class="!min-w-[200px] flex-1">
				<FormControl
					type="select"
					placeholder="Operator"
					:modelValue="state.operator"
					:options="operatorOptions"
					@update:modelValue="onOperatorChange($event)"
				/>
			</div>
			<div id="value" class="!min-w-[200px] flex-1 flex-shrink-0">
				<DatePicker
					v-if="valueSelectorType === 'date'"
					:range="false"
					:modelValue="[state.value as string]"
					@update:modelValue="state.value = $event[0]"
				></DatePicker>
				<DatePicker
					v-else-if="valueSelectorType === 'date_range'"
					:range="true"
					v-model="(state.value as string[])"
				></DatePicker>
				<RelativeDatePicker
					v-else-if="valueSelectorType === 'relative_date'"
					v-model="(state.value as string)"
				/>
				<ColumnFilterValueSelector
					v-else-if="valueSelectorType === 'select'"
					v-model="(state.value as string[])"
					:valuesProvider="props.valuesProvider"
				/>
				<FormControl
					v-else-if="valueSelectorType === 'text'"
					v-model="state.value"
					placeholder="Value"
					autocomplete="off"
				/>
			</div>
		</template>
		<div class="flex justify-end gap-2">
			<Button icon="x" @click="clearFilter"></Button>
			<Button icon="check" variant="solid" @click="applyFilter"></Button>
		</div>
	</div>
</template>
