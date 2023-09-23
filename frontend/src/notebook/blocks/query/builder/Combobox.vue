<script setup>
import UseTooltip from '@/components/UseTooltip.vue'
import { isInViewport } from '@/utils'
import { Combobox, ComboboxInput, ComboboxOption, ComboboxOptions } from '@headlessui/vue'
import { LoadingIndicator } from 'frappe-ui'
import { computed, ref } from 'vue'

const emit = defineEmits(['update:modelValue', 'filterInput'])
const props = defineProps({
	modelValue: Object,
	allowMultiple: Boolean,
	values: Array,
	loading: Boolean,
})

const selectedValue = computed({
	get: () => props.modelValue,
	set: (value) => emit('update:modelValue', value),
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

const optionsRef = ref(null)

// this is to manually trigger tooltip visibility
// because isInViewport isn't reactive so the component doesn't re-render
const canShowTooltip = ref(false)
</script>

<template>
	<Combobox
		as="div"
		class="p-0.5"
		:nullable="!props.allowMultiple"
		:multiple="Boolean(props.allowMultiple)"
		:value="props.allowMultiple ? multipleValues : selectedValue"
		@mouseover="canShowTooltip = true"
	>
		<ComboboxInput
			v-if="props.allowMultiple"
			autocomplete="off"
			placeholder="Filter..."
			class="form-input mb-1 block h-7 w-full border-gray-400 placeholder-gray-500"
		/>
		<ComboboxOptions
			static
			class="relative max-h-[15rem] w-full min-w-[10rem] max-w-[30rem] overflow-y-scroll"
		>
			<transition-group name="fade">
				<ComboboxOption
					v-for="(value, idx) in props.values"
					:key="value.value || idx"
					:value="value"
					v-slot="{ active }"
					@click.prevent.stop="select(value)"
				>
					<div
						ref="optionsRef"
						class="flex w-full cursor-pointer items-center justify-between rounded p-2 hover:bg-gray-100"
						:class="{
							'bg-gray-100': active,
						}"
					>
						<div class="flex flex-1 flex-grow-[5] items-center overflow-hidden">
							<FeatherIcon
								v-if="props.allowMultiple"
								:name="isSelected(value) ? 'check-square' : 'square'"
								class="mr-2 h-3.5 w-3.5"
								:class="isSelected(value) ? 'text-gray-900' : 'text-gray-400'"
							/>
							<span class="overflow-hidden text-ellipsis whitespace-nowrap">
								{{ value.label || value.value || 'No label' }}
							</span>
						</div>
						<span
							v-if="value.description"
							class="ml-4 w-fit overflow-hidden text-ellipsis whitespace-nowrap text-right text-gray-500"
						>
							{{ value.description }}
						</span>
					</div>

					<div
						v-if="
							canShowTooltip &&
							(value.tooltip || value.tooltip_component) &&
							isInViewport(optionsRef?.[idx])
						"
					>
						<UseTooltip
							:targetElement="optionsRef[idx]"
							:content="value.tooltip"
							:hoverDelay="0.1"
							placement="right-start"
						>
							<template #content="{ visible }" v-if="value.tooltip_component">
								<component
									v-if="visible"
									:option="value"
									:is="value.tooltip_component"
								/>
							</template>
						</UseTooltip>
					</div>
				</ComboboxOption>
				<ComboboxOption
					v-if="props.loading"
					class="flex items-center px-1.5 py-1 text-sm text-gray-500"
				>
					<LoadingIndicator class="h-4 w-4" />
					<span class="ml-2">Loading...</span>
				</ComboboxOption>
				<ComboboxOption
					v-else-if="props.values?.length === 0"
					class="px-1.5 pb-0 text-sm text-gray-500"
				>
					No results found
				</ComboboxOption>
			</transition-group>
		</ComboboxOptions>
	</Combobox>
</template>
