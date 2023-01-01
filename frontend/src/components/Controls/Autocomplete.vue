<template>
	<Combobox as="div" v-model="selectedOption" v-slot="{ open: isComboBoxOpen }" nullable>
		<ComboboxLabel v-if="label">{{ label }}</ComboboxLabel>
		<Popover ref="popover" class="flex w-full [&>div:first-child]:w-full">
			<template #target="{ togglePopover }">
				<ComboboxInput
					ref="input"
					autocomplete="off"
					:placeholder="placeholder"
					@focus="togglePopover(true)"
					@change="filterQuery = $event.target.value"
					:displayValue="(option) => option?.label"
					class="form-input block h-8 w-full placeholder-gray-500"
				>
				</ComboboxInput>
			</template>
			<template #body="{ isOpen: isPopoverOpen }">
				<transition
					enter-active-class="transition duration-100 ease-out"
					enter-from-class="transform scale-95 opacity-0"
					enter-to-class="transform scale-100 opacity-100"
					leave-active-class="transition duration-75 ease-out"
					leave-from-class="transform scale-100 opacity-100"
					leave-to-class="transform scale-95 opacity-0"
				>
					<div v-show="isComboBoxOpen || isPopoverOpen">
						<ComboboxOptions
							static
							class="my-1 max-h-48 w-full origin-top overflow-y-scroll rounded-md border bg-white p-1 shadow"
						>
							<div
								v-if="filteredOptions.length === 0 && !$props.allowCreate"
								class="flex h-8 w-full items-center rounded bg-gray-50 px-3 text-sm font-light"
							>
								{{ emptyText }}
							</div>
							<ComboboxOption
								v-if="$props.allowCreate"
								class="flex h-9 w-full cursor-pointer items-center rounded px-3 text-base text-blue-600 hover:bg-gray-100"
								@click.prevent="$emit('createOption', filterQuery)"
							>
								<FeatherIcon name="plus" class="mr-1 h-3.5 w-3.5" />
								Create New
							</ComboboxOption>
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
										'cursor-not-allowed !opacity-50': option.disabled,
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
import { ref, computed, watch, inject, onMounted, nextTick } from 'vue'
import {
	Combobox,
	ComboboxLabel,
	ComboboxInput,
	ComboboxOptions,
	ComboboxOption,
} from '@headlessui/vue'

const $utils = inject('$utils')

const emit = defineEmits([
	'update:modelValue',
	'inputChange',
	'selectOption',
	'blur',
	'createOption',
])
const props = defineProps({
	label: {
		type: String,
		default: '',
	},
	placeholder: {
		type: String,
		default: '',
	},
	emptyText: {
		type: String,
		default: 'No results found',
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
	allowCreate: {
		type: Boolean,
		default: false,
	},
	autofocus: {
		type: Boolean,
		default: true,
	},
})

const input = ref(null)
const popover = ref(null)
defineExpose({ input })
onMounted(() => {
	if (props.autofocus == false) {
		setTimeout(() => {
			input.value.$el.blur()
			popover.value.close()
		}, 0)
	}
})

const filterQuery = ref('')
const modelValueIsObject = computed(() => {
	return typeof props.modelValue === 'object' || !props.modelValue
})
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
		return modelValueIsObject.value
			? props.modelValue
			: options.value.find((option) => option.value === props.modelValue)
	},
	set(value) {
		if (value) {
			popover.value.close()
			input.value.$el.blur()
		}
		const _value = modelValueIsObject.value ? value : value.value
		emit('update:modelValue', _value)
		emit('selectOption', _value)
	},
})
const uniqueOptions = computed(() => {
	return options.value.filter((option, index, self) => {
		return (
			self.findIndex(
				(t) =>
					t.value === option.value &&
					t.label === option.label &&
					t.description === option.description
			) === index
		)
	})
})
const filteredOptions = computed(() => {
	return !filterQuery.value
		? uniqueOptions.value.slice(0, 50)
		: $utils
				.fuzzySearch(uniqueOptions.value, {
					term: filterQuery.value,
					keys: ['label', 'value', 'description'],
				})
				.slice(0, 50)
})

watch(filterQuery, (newValue, oldValue) => {
	if (newValue === oldValue) return
	emit('inputChange', newValue)
})
</script>
