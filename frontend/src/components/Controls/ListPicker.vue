<template>
	<Combobox multiple nullable v-slot="{ open: isComboboxOpen }" v-model="selectedOptions">
		<Popover class="w-full">
			<template #target="{ open: openPopover }">
				<div class="w-full">
					<ComboboxButton
						class="flex w-full items-center justify-between rounded-md bg-gray-100 py-1.5 pl-3 pr-2"
						:class="{ 'rounded-b-none': isComboboxOpen }"
						@click="
							() => {
								openPopover()
							}
						"
					>
						<span
							class="overflow-hidden text-ellipsis whitespace-nowrap text-left text-base"
							v-if="selectedOptions.length > 0"
						>
							{{ displayValue }}
						</span>
						<span class="text-base text-gray-500" v-else>
							{{ placeholder || '' }}
						</span>

						<FeatherIcon
							name="chevron-down"
							class="h-4 w-4 text-gray-500"
							aria-hidden="true"
						/>
					</ComboboxButton>
				</div>
			</template>
			<template #body>
				<ComboboxOptions
					class="max-h-[15rem] overflow-y-auto rounded-md rounded-t-none bg-white px-1.5 pb-1.5 shadow-md"
					static
					v-show="isComboboxOpen"
				>
					<div class="sticky top-0 mb-1.5 flex items-stretch space-x-1.5 bg-white pt-1.5">
						<ComboboxInput
							class="form-input w-full placeholder-gray-500"
							ref="input"
							type="text"
							@change="
								(e) => {
									query = e.target.value
									emit('inputChange', query)
								}
							"
							:value="query"
							autocomplete="off"
							placeholder="Search..."
						/>
						<Button icon="x" @click="selectedOptions = []" />
					</div>
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
						v-show="filteredOptions.length > 0"
						@click="
							() => {
								$refs.input.el.focus()
								// need to manually remove option from selectedOptions
								// because clicking on an option twice doesn't unselect it
								toggleSelection(option)
							}
						"
						v-slot="{ active }"
					>
						<div
							class="flex h-9 w-full cursor-pointer items-center justify-between rounded px-3 text-base"
							:class="{
								'bg-gray-100 text-gray-800': active,
								'bg-white': !active,
							}"
						>
							<span>{{ option.label }}</span>
							<FeatherIcon name="check" class="h-4 w-4" v-show="isSelected(option)" />
						</div>
					</ComboboxOption>
				</ComboboxOptions>
			</template>
		</Popover>
	</Combobox>
</template>

<script setup>
import { ref, computed, inject, useAttrs } from 'vue'
import {
	Combobox,
	ComboboxButton,
	ComboboxInput,
	ComboboxOptions,
	ComboboxOption,
} from '@headlessui/vue'

const emit = defineEmits(['inputChange', 'change', 'update:modelValue'])
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
		type: Array,
		default: [],
	},
	options: {
		type: Array,
		default: [],
	},
})

const query = ref('')

const options = computed(() => makeOptions(props.options.slice()))
function makeOptions(options) {
	// make sure options are objects with a label property and a value property with no duplicates

	if (!options || options.length === 0) {
		return []
	}

	if (options[0].hasOwnProperty('label') && options[0].hasOwnProperty('value')) {
		options = options
	}

	if (typeof options[0] === 'string') {
		options = options.map((option) => {
			return {
				label: option,
				value: option,
			}
		})
	}

	options = options.filter((option, index, self) => {
		return option && option.value && self.findIndex((t) => t.value === option.value) === index
	})

	return options
}

const attrs = useAttrs()
const valuePassed = attrs.hasOwnProperty('value')
const selectedOptions = computed({
	get() {
		return makeOptions(valuePassed ? attrs.value?.slice() : props.modelValue.slice())
	},
	set(val) {
		const event = valuePassed ? 'change' : 'update:modelValue'
		console.log('set selectedOptions', event, val)
		emit(event, val)
	},
})

function isSelected(option) {
	return selectedOptions.value.findIndex((t) => t.value === option.value) > -1
}
function toggleSelection(option) {
	if (isSelected(option)) {
		selectedOptions.value = selectedOptions.value.filter((t) => t.value !== option.value)
	} else {
		selectedOptions.value = [...selectedOptions.value, option]
	}
}

const $utils = inject('$utils')
const filteredOptions = computed(() => {
	return !query.value
		? options.value
		: $utils.fuzzySearch(options.value, {
				term: query.value,
				keys: ['label', 'value'],
		  })
})

const displayValue = computed(() => {
	const labels = selectedOptions.value[0].hasOwnProperty('label')
		? selectedOptions.value.map((option) => option.label)
		: selectedOptions.value

	return labels.join(', ')
})
</script>
