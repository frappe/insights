<script setup lang="ts">
import { Settings, XIcon } from 'lucide-vue-next'
import { watchEffect } from 'vue'
import DraggableList from '../../components/DraggableList.vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { copy } from '../../helpers'
import { Measure } from '../../types/query.types'
import { MeasureOption } from './ChartConfigForm.vue'

const props = defineProps<{
	options: MeasureOption[]
}>()

const measures = defineModel<Measure[]>({
	required: true,
	default: () => [],
})

watchEffect(() => {
	if (!measures.value.length) {
		if (props.options.length) {
			measures.value = [copy(props.options[0])]
		} else {
			addMeasure()
		}
	}
})

function addMeasure() {
	measures.value.push({} as MeasureOption)
}
</script>

<template>
	<div>
		<DraggableList v-model:items="measures" group="measures">
			<template #item="{ item, index }">
				<div class="flex gap-1">
					<div class="flex-1">
						<Autocomplete
							placeholder="Select a column"
							:showFooter="true"
							:options="props.options"
							:modelValue="item.measure_name"
							@update:modelValue="Object.assign(item, $event || {})"
						/>
					</div>
					<Popover v-if="item.measure_name" placement="bottom-end">
						<template #target="{ togglePopover }">
							<Button @click="togglePopover">
								<template #icon>
									<Settings class="h-4 w-4 text-gray-700" stroke-width="1.5" />
								</template>
							</Button>
						</template>
						<template #body-main>
							<div class="flex w-[14rem] flex-col gap-2 p-2">
								<InlineFormControlLabel label="Label">
									<FormControl
										v-model="item.measure_name"
										autocomplete="off"
										:debounce="500"
									/>
								</InlineFormControlLabel>

								<slot name="measure-fields" />

								<div class="flex gap-1">
									<Button
										class="w-full"
										@click="measures.splice(index, 1)"
										theme="red"
									>
										<template #prefix>
											<XIcon
												class="h-4 w-4 text-red-700"
												stroke-width="1.5"
											/>
										</template>
										Remove
									</Button>
								</div>
							</div>
						</template>
					</Popover>
					<Button v-else class="flex-shrink-0" @click="measures.splice(index, 1)">
						<template #icon>
							<XIcon class="h-4 w-4 text-gray-700" stroke-width="1.5" />
						</template>
					</Button>
				</div>
			</template>
		</DraggableList>

		<button class="mt-1.5 text-left text-xs text-gray-600 hover:underline" @click="addMeasure">
			+ Add column
		</button>
	</div>
</template>
