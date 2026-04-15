<script setup lang="ts">
import { computed, ref } from 'vue'
import { cachedCall } from '../../helpers'
import { COLUMN_TYPES, FIELDTYPES } from '../../helpers/constants'
import ExpressionEditor from '../../query/components/ExpressionEditor.vue'
import { expression } from '../../query/helpers'
import { __ } from '../../translation'
import { ColumnOption, ExpressionMeasure, MeasureDataType } from '../../types/query.types'

const props = defineProps<{
	measure?: ExpressionMeasure
	columnOptions: ColumnOption[]
}>()
const emit = defineEmits({ select: (measure: ExpressionMeasure) => true })
const showDialog = defineModel()

const columnTypes = COLUMN_TYPES.map((t) => t.value).filter((t) =>
	FIELDTYPES.NUMBER.includes(t),
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
		  },
)

const isValid = computed(() => {
	return newMeasure.value.name && newMeasure.value.type && newMeasure.value.expression.trim()
})

const validationState = ref<'unknown' | 'validating' | 'valid' | 'invalid'>('unknown')
const validationErrors = ref<Array<{ line?: number; column?: number; message: string }>>([])

async function confirmCalculation() {
	if (!isValid.value) return
	validationState.value = 'validating'
	validationErrors.value = []
	try {
		const res: any = await cachedCall(
			'insights.insights.doctype.insights_data_source_v3.ibis.utils.validate_expression',
			{
				expression: newMeasure.value.expression,
				column_options: JSON.stringify(props.columnOptions),
			},
		)

		if (!res || !res.is_valid) {
			validationState.value = 'invalid'
			validationErrors.value = res?.errors || [{ message: __('Validation failed') }]
			return
		}

		validationState.value = 'valid'
		emit('select', {
			measure_name: newMeasure.value.name,
			data_type: newMeasure.value.type,
			expression: expression(newMeasure.value.expression),
		})
		resetNewMeasure()
		showDialog.value = false
	} catch (e) {
		console.error(e)
		validationState.value = 'unknown'
		validationErrors.value = [{ message: __('Unexpected validation error') }]
	}
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
		:options="{ size: '2xl' }"
		:modelValue="Boolean(showDialog)"
		:disableOutsideClickToClose="true"
		@after-leave="resetNewMeasure"
		@close="showDialog = false"
	>
		<template #body>
			<div class="bg-white px-4 pb-6 pt-5 sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">
						{{ __('Create Measure') }}
					</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md" />
				</div>

				<div class="flex flex-col gap-2">
					<ExpressionEditor
						v-model="newMeasure.expression"
						class="column-expression"
						:column-options="props.columnOptions"
					/>
					<div class="flex gap-2">
						<FormControl
							type="text"
							class="flex-1"
							:label="__('Measure Name')"
							autocomplete="off"
							placeholder="Measure Name"
							v-model="newMeasure.name"
						/>
						<FormControl
							type="select"
							class="flex-1"
							:label="__('Data Type')"
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
							:label="__('Confirm')"
							variant="solid"
							:disabled="!isValid || validationState === 'validating'"
							@click="confirmCalculation"
						/>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<style>
div[data-dismissable-layer] {
	border-radius: 0.75rem;
}
.column-expression {
	& .cm-column-highlight {
		background-color: #ededed !important;
		border-radius: 0.5rem !important;
		padding: 1px 2px !important;
		border: 1px solid #dedede !important;
	}
	& .cm-scroller {
		background-color: #ffffff !important;
		border-radius: 0.5rem !important;
		border: 1px solid #ededed !important;
	}
}
</style>
