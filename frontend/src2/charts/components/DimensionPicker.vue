<script setup lang="ts">
import { XIcon } from 'lucide-vue-next'
import { watchEffect } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import { copy } from '../../helpers'
import { Dimension } from '../../types/query.types'
import { DimensionOption } from './ChartConfigForm.vue'

const props = defineProps<{
	options: DimensionOption[]
}>()

const dimensions = defineModel<Dimension[]>({
	required: true,
	default: () => [],
})

watchEffect(() => {
	if (!dimensions.value.length) {
		if (props.options.length) {
			dimensions.value = [copy(props.options[0])]
		} else {
			addDimension()
		}
	}
})

function addDimension() {
	dimensions.value.push({} as DimensionOption)
}
</script>

<template>
	<div>
		<DraggableList v-model:items="dimensions">
			<template #item="{ item, index }">
				<div class="flex gap-1">
					<div class="flex-1">
						<Autocomplete
							placeholder="Select a column"
							:showFooter="true"
							:options="props.options"
							:modelValue="item.column_name"
							@update:modelValue="Object.assign(item, $event || {})"
						/>
					</div>
					<Button class="flex-shrink-0" @click="dimensions.splice(index, 1)">
						<template #icon>
							<XIcon class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
				</div>
			</template>
		</DraggableList>

		<button
			class="mt-1.5 text-left text-xs text-gray-600 hover:underline"
			@click="addDimension"
		>
			+ Add column
		</button>
	</div>
</template>
