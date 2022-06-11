<template>
	<Popover class="flex w-full [&>div:first-child]:w-full">
		<template #target="{ togglePopover }">
			<div class="relative">
				<input
					readonly
					:placeholder="placeholder"
					@focus="
						() => {
							togglePopover(true)
							$nextTick(() => {
								$refs.input.el.focus()
							})
						}
					"
					class="form-input block h-8 w-full cursor-text select-none rounded-md px-3 placeholder-gray-500 focus:outline-none"
					:value="selectedOptions.length ? formatValue(selectedOptions) : ''"
				/>
				<div class="absolute top-0 right-3 flex h-full cursor-pointer items-center text-gray-500">
					<FeatherIcon
						name="x"
						@click="selectedOptions = []"
						v-show="selectedOptions.length > 0"
						class="h-4 w-4 hover:text-gray-700"
					/>
				</div>
			</div>
		</template>
		<template #body>
			<Combobox
				as="div"
				multiple
				nullable
				v-slot="{ open }"
				v-model="selectedOptions"
				class="my-1 rounded-md bg-white p-2 shadow"
			>
				<ComboboxLabel v-if="label">{{ label }}</ComboboxLabel>
				<ComboboxInput
					ref="input"
					placeholder="Search..."
					@change="
						(e) => {
							filter_query = e.target.value
							emit('inputChange', filter_query)
						}
					"
					class="form-input block h-8 w-full placeholder-gray-500"
				>
				</ComboboxInput>
				<transition
					enter-active-class="transition duration-100 ease-out"
					enter-from-class="transform scale-95 opacity-0"
					enter-to-class="transform scale-100 opacity-100"
					leave-active-class="transition duration-75 ease-out"
					leave-from-class="transform scale-100 opacity-100"
					leave-to-class="transform scale-95 opacity-0"
				>
					<div v-show="open && options.length > 0">
						<ComboboxOptions static class="mt-2 max-h-48 w-full origin-top overflow-y-scroll">
							<div
								v-if="filteredOptions.length === 0 && filter_query !== ''"
								class="flex h-8 w-full items-center rounded bg-gray-50 px-3 text-sm font-light"
							>
								No results found
							</div>
							<ComboboxOption
								v-for="(option, idx) in filteredOptions"
								:key="idx"
								:value="option"
								@click="$refs.input.el.focus()"
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
			</Combobox>
		</template>
	</Popover>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { Combobox, ComboboxLabel, ComboboxInput, ComboboxOptions, ComboboxOption } from '@headlessui/vue'

const emit = defineEmits(['inputChange', 'selectOption'])
const props = defineProps({
	label: {
		type: String,
		default: '',
	},
	placeholder: {
		type: String,
		default: '',
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

const filter_query = ref('')
const selectedOptions = ref([])

const filteredOptions = computed(() => {
	// filter out duplicates
	const options = props.options.filter((option, index, self) => {
		return self.findIndex((t) => t.value === option.value) === index
	})
	return !filter_query.value
		? options
		: options.filter((option) =>
				option.label.toLowerCase().replace(/\s+/g, '').includes(filter_query.value.toLowerCase().replace(/\s+/g, ''))
		  )
})

const formatValue = (options) => {
	const labels = options.map((option) => option.label)
	if (labels.length <= 2) {
		return labels.join(', ')
	}
	return `${labels[0]} & ${labels.length - 1} more`
}

watch(selectedOptions, (newValue) => emit('selectOption', newValue), { deep: true })
</script>
