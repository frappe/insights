<script setup lang="ts">
import { computed, ref } from 'vue'
import { COLUMN_TYPES, FIELDTYPES } from '../../helpers/constants'
import ExpressionEditor from '../../query/components/ExpressionEditor.vue'
import { expression } from '../../query/helpers'
import { ColumnOption, ExpressionMeasure, MeasureDataType } from '../../types/query.types'
import { cachedCall } from '../../helpers'
import CollapsibleSection from './CollapsibleSection.vue'
import { TextInput } from 'frappe-ui'

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
			}
		)

		if (!res || !res.is_valid) {
			validationState.value = 'invalid'
			validationErrors.value = res?.errors || [{ message: 'Validation failed' }]
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
		validationErrors.value = [{ message: 'Unexpected validation error' }]
	}
}

function resetNewMeasure() {
	newMeasure.value = {
		name: 'new_measure',
		type: columnTypes[0],
		expression: '',
	}
}

const functionList = ref<string[]>([])
const selectedFunction = ref<string>('')

const searchTerm = ref('')
const filteredFunctions = computed(() => {
	const searchQuery = searchTerm.value.trim().toLowerCase()
	if (!searchQuery) return functionList.value
	return functionList.value.filter((fn) => fn.toLowerCase().includes(searchQuery))
})

type FunctionSignature = {
	name: string
	definition: string
	description: string
	current_param: string
	current_param_description: string
	params: { name: string; description: string }[]
}
const functionDoc = ref<FunctionSignature | null>(null)

cachedCall('insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_list').then(
	(res: any) => {
		functionList.value = res
	}
)

function selectFunction(funcName: string) {
	selectedFunction.value = funcName

	cachedCall(
		'insights.insights.doctype.insights_data_source_v3.ibis.utils.get_function_description',
		{ funcName }
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
</script>

<template>
	<Dialog
		:modelValue="Boolean(showDialog)"
		@after-leave="resetNewMeasure"
		@close="!newMeasure.expression && (showDialog = false)"
		:options="{ size: 'xl' }"
	>
		<template #body>
			<div class="min-w-[30rem] flex flex-col gap-3 px-4 pb-6 pt-5">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Create Measure</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md" />
				</div>

				<div class="flex flex-col gap-3">
					<ExpressionEditor
						v-model="newMeasure.expression"
						:column-options="props.columnOptions"
						@function-signature-update="updateDocumentationFromEditor"
					/>
					<div
						v-if="validationErrors.length"
						class="mt-2 rounded border border-red-200 bg-red-50 p-3 text-sm text-red-800"
					>
						<div class="font-medium">Validation Errors</div>
						<ul class="mt-1 list-disc pl-5">
							<li v-for="(err, idx) in validationErrors" :key="idx">
								<span v-if="err.line !== undefined"
									>Lin {{ err.line }}, Col {{ err.column }}: </span
								>{{ err.message }}
							</li>
						</ul>
					</div>
					<CollapsibleSection title="Functions" :collapsed="true">
						<div class="flex h-[12rem] gap-4 border-t pt-4">
							<div class="w-[30%] flex flex-col border-r pr-4">
								<h4 class="mb-2 text-sm text-gray-600">Functions</h4>
								<TextInput
									v-model="searchTerm"
									type="text"
									placeholder="Search functions"
									class="w-full rounded-sm text-sm"
								/>
								<div class="flex-1 overflow-y-auto">
									<div
										v-if="filteredFunctions.length === 0"
										class="flex h-full w-full items-center justify-center"
									>
										<p class="text-sm text-gray-500">No functions found</p>
									</div>
									<div
										v-for="fn in filteredFunctions"
										:key="fn"
										@click="selectFunction(fn)"
										:class="[
											'cursor-pointer rounded-sm px-2 py-1.5 text-sm',
											selectedFunction === fn
												? 'bg-blue-50 text-blue-700'
												: 'hover:bg-gray-50 text-gray-700',
										]"
									>
										{{ fn }}
									</div>
								</div>
							</div>
							<div class="flex-1 overflow-y-auto">
								<div
									v-if="!functionDoc"
									class="flex h-full w-full items-center justify-center"
								>
									<p class="text-sm text-gray-500">
										Select a function to see details
									</p>
								</div>
								<div v-if="functionDoc" class="flex flex-col gap-3">
									<div
										v-if="functionDoc.definition"
										v-html="functionDoc.definition"
										class="font-mono text-sm text-gray-800 bg-gray-50 rounded p-2"
									></div>
									<div
										v-if="functionDoc.description"
										class="whitespace-pre-wrap text-sm text-gray-700"
									>
										{{ functionDoc.description }}
									</div>
									<div
										v-if="functionDoc.params?.length"
										class="flex flex-col gap-2"
									>
										<h5 class="text-sm font-medium text-gray-700">
											Parameters:
										</h5>
										<div
											v-for="param in functionDoc.params"
											:key="param.name"
											class="ml-2 text-sm"
										>
											<span class="font-mono font-medium text-gray-800">{{
												param.name
											}}</span>
											<span class="text-gray-600"
												>: {{ param.description }}</span
											>
										</div>
									</div>
								</div>
							</div>
						</div>
					</CollapsibleSection>

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

				<div class="mt-4 flex items-center justify-end gap-2">
					<Button
						label="Confirm"
						variant="solid"
						:disabled="!isValid || validationState === 'validating'"
						@click="confirmCalculation"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<style>
div[data-headlessui-state] {
	border-radius: 0.75rem;
}
</style>
