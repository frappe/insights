<script setup>
import UsePopover from '@/components/UsePopover.vue'
import { isEmptyObj } from '@/utils'
import { CornerLeftDown, CornerRightUp, Crop, Option, X } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import TransformEditor from './TransformEditor.vue'
import { Sigma } from 'lucide-vue-next'

const query = inject('query')
const assistedQuery = inject('assistedQuery')

const transformRefs = ref(null)
const activeTransformIdx = ref(null)

const transformTypeToIcon = {
	Pivot: CornerRightUp,
	Unpivot: CornerLeftDown,
	Transpose: Crop,
	CumulativeSum: Sigma,
}
const transformTypeToLabel = {
	Pivot: 'Convert Row to Column',
	Unpivot: 'Convert Column to Row',
	Transpose: 'Transpose',
	CumulativeSum: 'Cumulative Sum',
}

function onAddTransform() {
	assistedQuery.addTransform()
	activeTransformIdx.value = assistedQuery.transforms.length - 1
}
function onRemoveTransform() {
	assistedQuery.removeTransformAt(activeTransformIdx.value)
	activeTransformIdx.value = null
}
function onSaveTransform(transform) {
	assistedQuery.updateTransformAt(activeTransformIdx.value, transform)
	activeTransformIdx.value = null
}
function isValidTransform(transform) {
	return transform?.type && !isEmptyObj(transform.options)
}
</script>

<template>
	<div>
		<div class="mb-2 flex items-center justify-between">
			<div class="flex items-center space-x-1.5">
				<Option class="h-3.5 w-3.5 text-gray-600" />
				<p class="font-medium">Transform</p>
			</div>
			<Button variant="outline" icon="plus" @click.prevent.stop="onAddTransform"></Button>
		</div>
		<div class="space-y-2">
			<div
				ref="transformRefs"
				v-for="(transform, idx) in assistedQuery.transforms"
				:key="idx"
				class="group flex h-8 cursor-pointer items-center justify-between rounded border border-gray-300 bg-white px-2 hover:shadow"
				:class="
					activeTransformIdx === idx
						? 'border-gray-500 bg-white shadow-sm ring-1 ring-gray-400'
						: ''
				"
			>
				<!-- don't allow editing as the columns options are messed up -->
				<!-- @click="activeTransformIdx = assistedQuery.transforms.indexOf(transform)" -->
				<div class="flex w-full items-center overflow-hidden">
					<div class="flex w-full space-x-2 truncate" v-if="isValidTransform(transform)">
						<component
							:is="transformTypeToIcon[transform.type]"
							class="h-4 w-4 text-gray-600"
						/>
						<span class="truncate">{{ transformTypeToLabel[transform.type] }}</span>
					</div>
					<div v-else class="text-gray-600">Select a transform</div>
				</div>
				<div class="flex items-center space-x-2">
					<X
						class="invisible h-4 w-4 text-gray-600 transition-all hover:text-gray-800 group-hover:visible"
						@click.prevent.stop="assistedQuery.removeTransformAt(idx)"
					/>
				</div>
			</div>
		</div>
	</div>

	<UsePopover
		v-if="transformRefs?.[activeTransformIdx]"
		:show="activeTransformIdx !== null"
		@update:show="activeTransformIdx = null"
		:target-element="transformRefs[activeTransformIdx]"
		placement="right-start"
	>
		<div class="w-[20rem] rounded bg-white text-base shadow-2xl">
			<TransformEditor
				:transform="assistedQuery.transforms[activeTransformIdx]"
				@discard="activeTransformIdx = null"
				@remove="onRemoveTransform"
				@save="onSaveTransform"
			/>
		</div>
	</UsePopover>
</template>
