<script setup lang="ts">
import { ChevronDown, Settings, XIcon } from 'lucide-vue-next'
import InlineFormControlLabel from '../../components/InlineFormControlLabel.vue'
import { isDate } from '../../helpers'
import { COLUMN_TYPES, granularityOptions } from '../../helpers/constants'
import { Dimension, DimensionOption } from '../../types/query.types'
import LazyTextInput from '../../components/LazyTextInput.vue'

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

function selectDimension(option?: DimensionOption) {
	if (!option || !option.column_name) {
		dimension.value = {
			column_name: '',
			data_type: 'String',
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
			<Autocomplete
				placeholder="Select a column"
				:showFooter="true"
				:options="props.options"
				:modelValue="dimension.column_name"
				@update:modelValue="selectDimension"
			>
				<template #target="{ togglePopover }">
					<div class="flex w-full flex-col gap-1.5">
						<label v-if="props.label" class="block text-xs text-gray-600">
							{{ props.label }}
						</label>
						<Button @click="togglePopover" class="w-full !justify-start">
							<span
								class="truncate"
								:class="dimension.column_name ? 'text-gray-900' : 'text-gray-500'"
							>
								{{ dimension.dimension_name || 'Select a column' }}
							</span>
							<template #suffix>
								<ChevronDown
									class="ml-auto h-4 w-4 text-gray-700"
									stroke-width="1.5"
								/>
							</template>
						</Button>
					</div>
				</template>
			</Autocomplete>
		</div>
		<Popover v-if="dimension.column_name" placement="bottom-end">
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
						<LazyTextInput
							placeholder="Label"
							v-model="dimension.dimension_name"
						/>
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
						<Button class="w-full" @click="emit('remove')" theme="red">
							<template #prefix>
								<XIcon class="h-4 w-4 text-red-700" stroke-width="1.5" />
							</template>
							Remove
						</Button>
					</div>
				</div>
			</template>
		</Popover>
		<Button v-else @click="emit('remove')">
			<template #icon>
				<XIcon class="h-4 w-4 text-gray-700" stroke-width="1.5" />
			</template>
		</Button>
	</div>
</template>
