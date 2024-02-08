<script setup>
import { Option } from 'lucide-vue-next'
import { inject, ref } from 'vue'
import SectionHeader from './SectionHeader.vue'
import TransformEditor from './TransformEditor.vue'
import TransformListItem from './TransformListItem.vue'

const query = inject('query')
const assistedQuery = inject('assistedQuery')

const activeTransformIdx = ref(null)

async function onAddTransform() {
	assistedQuery.addTransform()
	setTimeout(() => {
		activeTransformIdx.value = assistedQuery.transforms.length - 1
	}, 500)
}
function onRemoveTransform() {
	assistedQuery.removeTransformAt(activeTransformIdx.value)
	activeTransformIdx.value = null
}
function onSaveTransform(transform) {
	assistedQuery.updateTransformAt(activeTransformIdx.value, transform)
	activeTransformIdx.value = null
}
</script>

<template>
	<div class="space-y-2">
		<SectionHeader title="Transform" :icon="Option" info="Apply transforms to the results.">
			<Button variant="outline" icon="plus" @click.prevent.stop="onAddTransform"></Button>
		</SectionHeader>
		<div class="space-y-2" v-if="assistedQuery.transforms.length">
			<template v-for="(transform, idx) in assistedQuery.transforms" :key="idx">
				<Popover
					:show="activeTransformIdx === idx"
					@close="activeTransformIdx === idx ? (activeTransformIdx = null) : null"
					placement="right-start"
				>
					<template #target="{ togglePopover }">
						<TransformListItem
							:transform="transform"
							:isActive="activeTransformIdx === idx"
							@edit="activeTransformIdx = idx"
							@remove="onRemoveTransform"
						/>
					</template>
					<template #body>
						<div
							v-if="activeTransformIdx === idx"
							class="ml-2 min-w-[20rem] rounded-lg border border-gray-100 bg-white text-base shadow-xl transition-all"
						>
							<TransformEditor
								:transform="assistedQuery.transforms[activeTransformIdx]"
								@discard="activeTransformIdx = null"
								@remove="onRemoveTransform"
								@save="onSaveTransform"
							/>
						</div>
					</template>
				</Popover>
			</template>
		</div>
	</div>
</template>
