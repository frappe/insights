<script setup lang="ts">
import { computed, ref } from 'vue'
import { __ } from '../../translation'
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

function confirmCalculation() {
	if (!isValid.value) return
<<<<<<< HEAD
	emit('select', {
		measure_name: newMeasure.value.name,
		data_type: newMeasure.value.type,
		expression: expression(newMeasure.value.expression),
	})
	resetNewMeasure()
	showDialog.value = false
=======
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
>>>>>>> 3144968c (fix: translate strings in src2 folder (#927))
}
function resetNewMeasure() {
	newMeasure.value = {
		name: 'new_measure',
		type: columnTypes[0],
		expression: '',
	}
}
<<<<<<< HEAD
=======

type FunctionListItem = {
	name: string
	type: 'function' | 'column'
	dataType?: string
}

const functionList = ref<FunctionListItem[]>([])
const selectedFunction = ref<string>('')

const searchTerm = ref('')
const filteredFunctions = computed(() => {
	const searchQuery = searchTerm.value.trim().toLowerCase()
	if (!searchQuery) return functionList.value
	return functionList.value.filter((item) => item.name.toLowerCase().includes(searchQuery))
})

type FunctionSignature = {
	name: string
	definition: string
	description: string
	examples?: string[]
	current_param?: string
	current_param_description?: string
	params?: { name: string; description: string }[]
}
const functionDoc = ref<FunctionSignature | null>(null)

const columnItems: FunctionListItem[] = props.columnOptions.map((c) => ({
	name: c.label,
	type: 'column' as const,
	dataType: c.data_type,
}))

cachedCall('insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_list').then(
	(res) => {
		const functionItems: FunctionListItem[] = res.map((fn: string) => ({
			name: fn,
			type: 'function' as const,
		}))
		functionList.value = [...functionItems, ...columnItems]
	},
)

function selectFunction(item: FunctionListItem) {
	selectedFunction.value = item.name

	cachedCall(
		'insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_description',
		{ funcName: item.name },
	)
		.then((res: any) => {
			if (res) {
				functionDoc.value = res
			}
		})
		.catch(console.error)
}

function updateDocumentationFromEditor(currentFunction: any) {
	if (currentFunction) {
		functionDoc.value = currentFunction
		selectedFunction.value = currentFunction.name
	}
}
>>>>>>> 3144968c (fix: translate strings in src2 folder (#927))
</script>

<template>
	<Dialog
		:modelValue="Boolean(showDialog)"
		:disableOutsideClickToClose="true"
<<<<<<< HEAD
		:options="{ title: 'Create Measure' }"
		@after-leave="resetNewMeasure"
		@close="showDialog = false"
	>
		<template #body-content>
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
=======
		:options="{ title: __('Create Measure'), size: '2xl' }"
		@after-leave="resetNewMeasure"
		@close="showDialog = false"
	>
		<template #body>
			<div class="min-w-[30rem] flex flex-col px-4 pb-4 pt-3">
				<div class="flex justify-between pb-2">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Create Measure</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md" />
				</div>

				<div class="flex flex-col gap-3">
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
					<ExpressionEditor
						v-model="newMeasure.expression"
						class="column-expression"
						:column-options="props.columnOptions"
						@function-signature-update="updateDocumentationFromEditor"
>>>>>>> 3144968c (fix: translate strings in src2 folder (#927))
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
		</template>
	</Dialog>
</template>
<<<<<<< HEAD
=======

<style lang="scss">
div[data-dismissable-layer] {
	border-radius: 0.75rem;
}
.column-expression {
	.cm-column-highlight {
		background-color: #ededed !important;
		border-radius: 2px !important;
		padding: 1px 2px !important;
		border: 1px solid #dedede !important;
	}
	.cm-scroller {
		background-color: #ffffff !important;
		border-radius: 4px !important;
		border: 1px solid #ededed !important;
	}
}
</style>
>>>>>>> 3144968c (fix: translate strings in src2 folder (#927))
