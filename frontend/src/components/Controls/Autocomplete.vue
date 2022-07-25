<template>
	<Combobox v-model="selectedOption" v-slot="{ open }" nullable>
		<ComboboxLabel v-if="label">{{ label }}</ComboboxLabel>
		<Popover class="flex w-full">
			<template #target="{ togglePopover }">
				<ComboboxInput
					ref="input"
					:placeholder="placeholder"
					@focus="togglePopover"
					@change="
						(e) => {
							filterQuery = e.target.value
							togglePopover(true)
						}
					"
					:displayValue="(option) => option?.label"
					class="form-input block h-8 w-full placeholder-gray-500"
				>
				</ComboboxInput>
			</template>
			<template #body>
				<transition
					enter-active-class="transition duration-100 ease-out"
					enter-from-class="transform scale-95 opacity-0"
					enter-to-class="transform scale-100 opacity-100"
					leave-active-class="transition duration-75 ease-out"
					leave-from-class="transform scale-100 opacity-100"
					leave-to-class="transform scale-95 opacity-0"
				>
					<!-- `open` is `true` only when first input even is fired on ComboboxInput -->
					<!-- So, before input event is fired on the input, filterQuery is empty, so we can display the options  -->
					<div v-show="!filterQuery || open">
						<ComboboxOptions
							static
							class="my-1 max-h-48 w-full origin-top overflow-y-scroll rounded-md border bg-white p-1 shadow"
						>
							<div
								v-if="filteredOptions.length === 0"
								class="flex h-8 w-full items-center rounded bg-gray-50 px-3 text-sm font-light"
							>
								No results found
							</div>
							<ComboboxOption
								v-for="(option, idx) in filteredOptions"
								:key="idx"
								:value="option"
								:disabled="option.disabled"
								v-slot="{ active, selected }"
							>
								<div
									class="flex h-9 w-full cursor-pointer items-center justify-between rounded px-3 text-base"
									:class="{
										'bg-gray-100 text-gray-800': active,
										'bg-white': !active,
										'!h-7 cursor-default !text-sm text-gray-600':
											option.disabled,
									}"
								>
									<div class="flex items-baseline space-x-2">
										<span>{{ option.label }}</span>
										<span
											v-if="option.description"
											class="text-sm font-light text-gray-500"
										>
											{{ option.description }}
										</span>
									</div>
									<FeatherIcon name="check" class="h-4 w-4" v-show="selected" />
								</div>
							</ComboboxOption>
						</ComboboxOptions>
					</div>
				</transition>
			</template>
		</Popover>
	</Combobox>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import {
	Combobox,
	ComboboxLabel,
	ComboboxInput,
	ComboboxOptions,
	ComboboxOption,
} from '@headlessui/vue'

const input = ref(null)
defineExpose({ input })

const emit = defineEmits(['update:modelValue', 'inputChange', 'selectOption', 'blur'])
const props = defineProps({
	label: {
		type: String,
		default: '',
	},
	placeholder: {
		type: String,
		default: '',
	},
	modelValue: {
		required: true,
	},
	options: {
		type: Array,
		default: () => [],
		required: true,
		validate: (value) => {
			return value.every((option) => {
				return typeof option.label === 'string' && typeof option.value === 'string'
			})
		},
	},
})

const filterQuery = ref('')
const options = computed(() => {
	if (typeof props.options[0] !== 'object') {
		return props.options.map((option) => {
			return {
				label: option,
				value: option,
			}
		})
	}
	return props.options
})
const selectedOption = computed({
	get() {
		return options.value.find((option) => option.value === props.modelValue?.value)
	},
	set(value) {
		emit('update:modelValue', value)
		emit('selectOption', value)
	},
})
const uniqueOptions = computed(() => {
	return options.value.filter((option, index, self) => {
		return self.findIndex((t) => t.value === option.value) === index
	})
})
const filteredOptions = computed(() => {
	return !filterQuery.value
		? uniqueOptions.value.slice(0, 50)
		: uniqueOptions.value
				.filter((option) =>
					option.label
						.toLowerCase()
						.replace(/\s+/g, '')
						.includes(filterQuery.value.toLowerCase().replace(/\s+/g, ''))
				)
				.slice(0, 50)
})

watch(filterQuery, (newValue, oldValue) => {
	if (newValue === oldValue) return

	if (newValue === '') {
		selectedOption.value = undefined
	}
	emit('inputChange', newValue)
})
</script>
