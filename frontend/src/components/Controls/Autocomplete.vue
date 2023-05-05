<template>
	<Combobox as="div" v-model="selectedOption" v-slot="{ open: isComboBoxOpen }" nullable>
		<ComboboxLabel v-if="label">{{ label }}</ComboboxLabel>
		<Popover ref="popover" class="relative flex w-full [&>div:first-child]:w-full">
			<template #target="{ togglePopover }">
				<ComboboxInput
					ref="input"
					autocomplete="off"
					:placeholder="placeholder"
					@click="togglePopover(true)"
					@blur="handleBlur($event, togglePopover)"
					@change="filterQuery = $event.target.value"
					:displayValue="(option) => option?.label"
					class="form-input block w-full placeholder-gray-500"
				>
				</ComboboxInput>
				<div v-if="loading" class="absolute right-2 flex h-full items-center">
					<LoadingIndicator class="h-3 w-3" />
				</div>
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
					<div v-show="!loading && (isComboBoxOpen || isPopoverOpen)">
						<ComboboxOptions
							static
							class="max-h-48 w-full origin-top overflow-y-scroll rounded-md border bg-white p-1 shadow"
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
								@click="createOption"
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
import {
	Combobox,
	ComboboxInput,
	ComboboxLabel,
	ComboboxOption,
	ComboboxOptions,
} from '@headlessui/vue'
import { LoadingIndicator } from 'frappe-ui'
import { computed, inject, onMounted, ref, watch } from 'vue'

const $utils = inject('$utils')

const emit = defineEmits(['update:modelValue', 'inputChange', 'change', 'blur', 'createOption'])
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
	value: {},
	valueModifiers: {
		type: Object,
		default: () => ({}),
	},
	modelValue: {},
	modelModifiers: {
		type: Object,
		default: () => ({}),
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
	loading: {
		type: Boolean,
		default: false,
	},
})

const input = ref(null)
const popover = ref(null)
defineExpose({ input })

const blur = () => (input.value.$el.blur(), popover.value.close(), emit('blur'))
const focus = () => (input.value.$el.focus(), popover.value.open())
onMounted(() => {
	if (props.autofocus == false) {
		setTimeout(blur, 0)
	}
})

const filterQuery = ref('')
const valueProp = props.modelValue ? 'modelValue' : 'value'
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
const returnValues = computed(() => {
	// if v-model.value is set, then return the value of the option
	return props.valueModifiers?.value || props.modelModifiers?.value
})
const selectedOption = computed({
	get() {
		return returnValues.value
			? options.value.find((option) => option.value === props[valueProp])
			: props[valueProp]
	},
	set(newOption) {
		if (newOption) blur()
		const _value = returnValues.value ? newOption?.value : newOption
		emit('update:modelValue', _value)
		emit('change', _value)
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
	focus()
})

function createOption() {
	emit('createOption', filterQuery.value)
	filterQuery.value = ''
	blur()
}

function handleBlur(event, close) {
	// on clicking the list item, the blur event is fired,
	// and the popover is closed before the list item is selected
	// so, we need to check if the click was on the list item and prevent closing
	// closing will be handled by the list item click event
	const shouldClose = event.relatedTarget?.classList.contains('form-input')
	if (shouldClose) {
		setTimeout(blur, 0)
	}
}
</script>
