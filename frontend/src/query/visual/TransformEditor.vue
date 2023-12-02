<script setup>
import { isEmptyObj } from '@/utils'
import { computed, defineProps, inject, reactive } from 'vue'
import CumulativeSumTransformFields from './CumulativeSumTransformFields.vue'
import PivotTransformFields from './PivotTransformFields.vue'
import { NEW_TRANSFORM } from './constants'

const emit = defineEmits(['save', 'discard', 'remove'])
const props = defineProps({ transform: Object })

const assistedQuery = inject('assistedQuery')
const query = inject('query')

const activeTransform = reactive({
	...NEW_TRANSFORM,
	...props.transform,
})
if (!activeTransform.type) activeTransform.type = 'Pivot'
if (!activeTransform.options) activeTransform.options = {}

const transformTypes = [
	{ label: 'Select Transform Type', value: '', disabled: true },
	{ label: 'Pivot', value: 'Pivot' },
	// { label: 'Unpivot', value: 'Unpivot' },
	// { label: 'Transpose', value: 'Transpose' },
	{ label: 'Cumulative Sum', value: 'CumulativeSum' },
]

const isValidTransform = computed(
	() => activeTransform?.type && !isEmptyObj(activeTransform.options)
)
</script>

<template>
	<div class="flex flex-col gap-4 p-4">
		<div class="space-y-1">
			<span class="text-sm font-medium text-gray-700">Type</span>
			<FormControl
				type="select"
				v-model="activeTransform.type"
				placeholder="Select Transform Type"
				:options="transformTypes"
				@update:modelValue="activeTransform.options = {}"
			/>
		</div>
		<PivotTransformFields
			v-if="activeTransform.type == 'Pivot'"
			v-model:transformOptions="activeTransform.options"
		></PivotTransformFields>
		<CumulativeSumTransformFields
			v-else-if="activeTransform.type == 'CumulativeSum'"
			v-model:transformOptions="activeTransform.options"
		></CumulativeSumTransformFields>
		<div class="flex justify-between">
			<Button variant="outline" @click="emit(isValidTransform ? 'discard' : 'remove')">
				Discard
			</Button>
			<div class="flex gap-2">
				<Button variant="outline" theme="red" @click="emit('remove')">Remove</Button>
				<Button
					variant="solid"
					:disabled="!isValidTransform"
					@click="emit('save', activeTransform)"
				>
					Save
				</Button>
			</div>
		</div>
	</div>
</template>
