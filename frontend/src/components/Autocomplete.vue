<template>
	<Combobox v-model="selectedOption" v-slot="{ open }" nullable>
		<ComboboxLabel v-if="label">{{ label }}</ComboboxLabel>
		<Popover class="flex w-full [&>div:first-child]:w-full">
			<template #target="{ togglePopover }">
				<ComboboxInput
					ref="input"
					:placeholder="placeholder"
					@focus="togglePopover(true)"
					@change="query = $event.target.value"
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
					<div v-show="open && options.length > 0">
						<ComboboxOptions
							static
							class="my-1 max-h-48 w-full origin-top overflow-y-scroll rounded-md border bg-white p-1 shadow"
						>
							<div
								v-if="filteredOptions.length === 0 && query !== ''"
								class="flex h-8 w-full items-center rounded bg-gray-50 px-3 text-sm font-light"
							>
								No results found
							</div>
							<ComboboxOption
								v-for="(option, idx) in filteredOptions"
								:key="idx"
								:value="option"
								v-slot="{ active, selected }"
							>
								<div
									class="flex h-9 w-full cursor-pointer items-center justify-between rounded px-3 text-base"
									:class="{
										'bg-gray-100 text-gray-800': active,
										'bg-white': !active,
									}"
								>
									<span>{{ option.label }}</span>
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
import { Combobox, ComboboxLabel, ComboboxInput, ComboboxOptions, ComboboxOption } from '@headlessui/vue'

const emit = defineEmits(['update:modelValue', 'inputChange'])
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
		type: Object,
		default: {},
	},
	options: {
		type: Array,
		default: () => [],
		validate: (value) => {
			return value.every((option) => {
				return typeof option.label === 'string' && typeof option.value === 'string'
			})
		},
	},
})

const query = ref('')
const selectedOption = ref(props.modelValue.value || {})
const filteredOptions = computed(() =>
	query.value === ''
		? props.options
		: props.options.filter((option) =>
				option.label.toLowerCase().replace(/\s+/g, '').includes(query.value.toLowerCase().replace(/\s+/g, ''))
		  )
)

watch(query, (newValue) => {
	if (newValue === '') {
		selectedOption.value = {}
	}
	emit('inputChange', newValue)
})
watch(selectedOption, (newValue) => {
	emit('update:modelValue', newValue)
})
</script>
