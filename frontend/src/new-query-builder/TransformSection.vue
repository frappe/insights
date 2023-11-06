<script setup>
import UsePopover from '@/components/UsePopover.vue'
import { isEmptyObj } from '@/utils'
import { Option, X } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import TransformEditor from './TransformEditor.vue'
import { CornerRightUp } from 'lucide-vue-next'
import { CornerLeftDown } from 'lucide-vue-next'
import { Crop } from 'lucide-vue-next'

const query = inject('query')
const builder = inject('builder')

const transformRefs = ref(null)
const activeTransformIdx = ref(null)

const transformTypeToIcon = {
	Pivot: CornerRightUp,
	Unpivot: CornerLeftDown,
	Transpose: Crop,
}
const transformTypeToLabel = {
	Pivot: 'Convert Row to Column',
	Unpivot: 'Convert Column to Row',
	Transpose: 'Transpose',
}

function onAddTransform() {
	builder.addTransform()
	activeTransformIdx.value = builder.transforms.length - 1
}
function onRemoveTransform() {
	builder.removeTransformAt(activeTransformIdx.value)
	activeTransformIdx.value = null
}
function onSaveTransform(transform) {
	builder.updateTransformAt(activeTransformIdx.value, transform)
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
				v-for="(transform, idx) in builder.transforms"
				:key="idx"
				class="group flex h-8 cursor-pointer items-center justify-between rounded border border-gray-300 bg-white px-2 hover:shadow"
				@click="activeTransformIdx = builder.transforms.indexOf(transform)"
			>
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
						@click.prevent.stop="builder.removeTransformAt(idx)"
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
	>
		<div class="w-[19rem] rounded bg-white text-base shadow-2xl">
			<TransformEditor
				:transform="builder.transforms[activeTransformIdx]"
				@discard="activeTransformIdx = null"
				@remove="onRemoveTransform"
				@save="onSaveTransform"
			/>
		</div>
	</UsePopover>
</template>
