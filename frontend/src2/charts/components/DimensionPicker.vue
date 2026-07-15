<script setup lang="ts">
import { ChevronDown, Settings, XIcon } from 'lucide-vue-next'
import { computed, watchEffect } from 'vue'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import LazyTextInput from '../../components/LazyTextInput.vue'
import { isDate } from '../../helpers'
import { COLUMN_TYPES, getDefaultGranularity, getGranularityOptions } from '../../helpers/constants'
import { Dimension, DimensionOption } from '../../types/query.types'

const emit = defineEmits({ remove: () => true })
const props = defineProps<{
	label?: string
	options: DimensionOption[]
}>()

const dimension = defineModel<Dimension>({
	required: true,
	default: () => {
		return {
			column_name: '',
			data_type: 'String',
			dimension_name: '',
		}
	},
})

if (!dimension.value.dimension_name && dimension.value.column_name) {
	dimension.value.dimension_name = dimension.value.column_name
}

const granularityOptions = computed(() => getGranularityOptions(dimension.value.data_type))

watchEffect(() => {
	const allowedGranularities = new Set(granularityOptions.value.map((option) => option.value))

	if (!allowedGranularities.size) {
		dimension.value.granularity = undefined
		return
	}

	if (!dimension.value.granularity || !allowedGranularities.has(dimension.value.granularity)) {
		dimension.value.granularity = getDefaultGranularity(dimension.value.data_type)
	}
})

function selectDimension(option?: DimensionOption) {
	if (!option || !option.column_name) {
		dimension.value = {
			column_name: '',
			data_type: 'String',
			granularity: undefined,
			dimension_name: '',
		}
		return
	}
	dimension.value = option
}
</script>

<template>
	<div class="flex items-end gap-1 overflow-hidden">
		<div class="flex-1 overflow-hidden">
			<Combobox
				placeholder="Select a column"
				:options="props.options"
				:modelValue="dimension.column_name"
				@update:selectedOption="selectDimension"
			>
				<template #trigger>
					<div class="flex w-full flex-col gap-1.5">
						<label v-if="props.label" class="block text-xs text-ink-gray-5">
							{{ props.label }}
						</label>
						<Button class="w-full !justify-start">
							<span
								class="truncate"
								:class="
									dimension.column_name ? 'text-ink-gray-8' : 'text-ink-gray-4'
								"
							>
								{{ dimension.dimension_name || 'Select a column' }}
							</span>
							<template #suffix>
								<ChevronDown
									class="ml-auto h-4 w-4 text-ink-gray-6"
									stroke-width="1.5"
								/>
							</template>
						</Button>
					</div>
				</template>
			</Combobox>
		</div>
		<Popover v-if="dimension.column_name" side="bottom" align="end">
			<template #trigger>
				<Button>
					<template #icon>
						<Settings class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
					</template>
				</Button>
			</template>
			<template #default>
				<div class="flex w-[14rem] flex-col gap-2 p-2">
					<InlineFormControlLabel label="Label">
						<LazyTextInput placeholder="Label" v-model="dimension.dimension_name" />
					</InlineFormControlLabel>

					<InlineFormControlLabel label="Type">
						<FormControl
							type="select"
							v-model="dimension.data_type"
							:options="COLUMN_TYPES"
						/>
					</InlineFormControlLabel>

					<InlineFormControlLabel v-if="isDate(dimension.data_type)" label="Granularity">
						<FormControl
							type="select"
							v-model="dimension.granularity"
							:options="granularityOptions"
						/>
					</InlineFormControlLabel>

					<slot name="config-fields" />

					<div class="flex gap-1">
						<Button
							class="w-full"
							variant="outline"
							theme="red"
							iconLeft="lucide-x"
							@click="emit('remove')"
						>
							Remove
						</Button>
					</div>
				</div>
			</template>
		</Popover>
		<Button v-else @click="emit('remove')">
			<template #icon>
				<XIcon class="h-4 w-4 text-ink-gray-6" stroke-width="1.5" />
			</template>
		</Button>
	</div>
</template>
