<script setup>
import { Combobox, ComboboxInput, ComboboxOption, ComboboxOptions } from '@headlessui/vue'
import { computed } from 'vue'

const emit = defineEmits(['update:modelValue', 'filterInput'])
const props = defineProps({
	modelValue: Object,
	allowMultiple: Boolean,
	values: Array,
})

const selectedValue = computed({
	get: () => {
		return props.modelValue
	},
	set: (value) => {
		emit('update:modelValue', value)
	},
})

const multipleValues = computed(() => {
	return selectedValue.value?.value || []
})
function select(value) {
	if (props.allowMultiple) {
		const oldValues = multipleValues.value
		const newValues = isSelected(value)
			? oldValues.filter((v) => v.value !== value.value)
			: [...oldValues, value]

		selectedValue.value = {
			label: newValues.length ? `${newValues.length} selected` : '',
			value: newValues,
		}
	} else {
		selectedValue.value = value
	}
}

function isSelected(value) {
	if (props.allowMultiple) {
		return multipleValues.value.some((v) => v.value === value.value)
	} else {
		return selectedValue.value?.value === value.value
	}
}
</script>

<template>
	<Combobox
		as="div"
		class="p-1.5"
		:nullable="!props.allowMultiple"
		:multiple="Boolean(props.allowMultiple)"
		:value="props.allowMultiple ? multipleValues : selectedValue"
	>
		<ComboboxInput
			v-if="props.allowMultiple"
			autocomplete="off"
			placeholder="Filter..."
			class="form-input mb-1 block h-7 w-full placeholder-gray-500"
		/>
		<ComboboxOptions
			static
			class="relative max-h-[15rem] w-full min-w-[10rem] max-w-[30rem] overflow-y-scroll"
		>
			<transition-group name="fade">
				<ComboboxOption
					v-for="value in props.values"
					:key="value.value"
					:value="value"
					v-slot="{ active }"
					@click.prevent.stop="select(value)"
				>
					<div
						class="flex w-full cursor-pointer items-center justify-between rounded-md px-1.5 py-2 hover:bg-gray-100"
						:class="{
							'bg-gray-100': active,
						}"
					>
						<div class="flex flex-1 flex-grow-[5] items-center overflow-hidden">
							<FeatherIcon
								v-if="props.allowMultiple"
								:name="isSelected(value) ? 'check-square' : 'square'"
								class="mr-2 h-3.5 w-3.5"
							/>
							<span class="overflow-hidden text-ellipsis whitespace-nowrap">
								{{ value.label || value.value || value }}
							</span>
						</div>
						<span
							v-if="value.description"
							class="ml-4 w-fit overflow-hidden text-ellipsis whitespace-nowrap text-right text-gray-400"
						>
							{{ value.description }}
						</span>
					</div>
				</ComboboxOption>
				<ComboboxOption
					v-if="props.values?.length === 0"
					class="px-1.5 pb-0 text-sm text-gray-400"
				>
					No results found
				</ComboboxOption>
			</transition-group>
		</ComboboxOptions>
	</Combobox>
</template>
