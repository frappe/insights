<script setup lang="ts">
import { computed, ref } from 'vue'
import { COLUMN_TYPES, FIELDTYPES } from '../../helpers/constants'
import ExpressionEditor from '../../query/components/ExpressionEditor.vue'
import { expression } from '../../query/helpers'
import { ColumnOption, ExpressionMeasure, MeasureDataType } from '../../types/query.types'

const props = defineProps<{
	measure?: ExpressionMeasure
	columnOptions: ColumnOption[]
}>()
const emit = defineEmits({ select: (measure: ExpressionMeasure) => true })
const showDialog = defineModel()

const columnTypes = COLUMN_TYPES.map((t) => t.value).filter((t) =>
	FIELDTYPES.NUMBER.includes(t)
) as MeasureDataType[]

const newMeasure = ref(
	props.measure?.expression?.expression
		? {
				name: props.measure.measure_name,
				type: props.measure.data_type,
				expression: props.measure.expression.expression,
		  }
		: {
				name: 'new_measure',
				type: columnTypes[0],
				expression: '',
		  }
)

const isValid = computed(() => {
	return newMeasure.value.name && newMeasure.value.type && newMeasure.value.expression.trim()
})

function confirmCalculation() {
	if (!isValid.value) return
	emit('select', {
		measure_name: newMeasure.value.name,
		data_type: newMeasure.value.type,
		expression: expression(newMeasure.value.expression),
	})
	resetNewMeasure()
	showDialog.value = false
}
function resetNewMeasure() {
	newMeasure.value = {
		name: 'new_measure',
		type: columnTypes[0],
		expression: '',
	}
}
</script>

<template>
	<Dialog
		:modelValue="Boolean(showDialog)"
		@after-leave="resetNewMeasure"
		@close="!newMeasure.expression && (showDialog = false)"
	>
		<template #body>
			<div class="bg-white px-4 pb-6 pt-5 sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Create Measure</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md">
					</Button>
				</div>
				<div class="flex flex-col gap-2">
					<ExpressionEditor
						v-model="newMeasure.expression"
						:column-options="props.columnOptions"
					/>
					<div class="flex gap-2">
						<FormControl
							type="text"
							class="flex-1"
							label="Measure Name"
							autocomplete="off"
							placeholder="Measure Name"
							v-model="newMeasure.name"
						/>
						<FormControl
							type="select"
							class="flex-1"
							label="Data Type"
							autocomplete="off"
							:options="columnTypes"
							v-model="newMeasure.type"
						/>
					</div>
				</div>
				<div class="mt-2 flex items-center justify-between gap-2">
					<div></div>
					<div class="flex items-center gap-2">
						<Button
							label="Confirm"
							variant="solid"
							:disabled="!isValid"
							@click="confirmCalculation"
						/>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
