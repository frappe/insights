<template>
	<Combobox
		v-model="selectedValue"
		:multiple="multiple"
		nullable
		v-slot="{ open: isComboboxOpen }"
	>
		<Popover class="w-full" v-model:show="showOptions">
			<template #target="{ open: openPopover, togglePopover }">
				<slot name="target" v-bind="{ open: openPopover, togglePopover }">
					<div class="w-full">
						<button
							class="flex h-7 w-full items-center justify-between gap-2 rounded bg-gray-100 py-1 px-2 transition-colors hover:bg-gray-200 focus:ring-2 focus:ring-gray-400"
							:class="{ 'bg-gray-200': isComboboxOpen }"
							@click="() => togglePopover()"
						>
							<div class="flex flex-1 items-center overflow-hidden">
								<slot name="prefix" />
								<span
									v-if="selectedValue"
									class="flex-1 truncate text-left text-base leading-5"
								>
									{{ displayValue(selectedValue) }}
								</span>
								<span v-else class="text-base leading-5 text-gray-600">
									{{ placeholder || '' }}
								</span>
								<slot name="suffix" />
							</div>
							<FeatherIcon
								name="chevron-down"
								class="h-4 w-4 text-gray-600"
								aria-hidden="true"
							/>
						</button>
					</div>
				</slot>
			</template>
			<template #body="{ isOpen, togglePopover }">
				<div v-show="isOpen">
					<div
						class="relative mt-1 rounded-lg bg-white text-base shadow-2xl"
						:class="bodyClasses"
					>
						<ComboboxOptions class="max-h-[15rem] overflow-y-auto px-1.5 pb-1.5" static>
							<div
								v-if="!hideSearch"
								class="sticky top-0 z-10 flex items-stretch space-x-1.5 bg-white py-1.5"
							>
								<div class="relative w-full">
									<ComboboxInput
										ref="searchInput"
										class="form-input w-full"
										type="text"
										@change="
											(e) => {
												query = e.target.value
											}
										"
										:value="query"
										autocomplete="off"
										placeholder="Search"
									/>
									<button
										class="absolute right-0 inline-flex h-7 w-7 items-center justify-center"
										@click="selectedValue = null"
									>
										<FeatherIcon name="x" class="w-4" />
									</button>
								</div>
							</div>
							<div
								v-for="group in groups"
								:key="group.key"
								v-show="group.items.length > 0"
							>
								<div
									v-if="group.group && !group.hideLabel"
									class="sticky top-10 truncate bg-white px-2.5 py-1.5 text-sm font-medium text-gray-600"
								>
									{{ group.group }}
								</div>
								<ComboboxOption
									as="template"
									v-for="(option, idx) in group.items.slice(0, 50)"
									:key="option?.value || idx"
									:value="option"
									v-slot="{ active, selected }"
								>
									<li
										:class="[
											'flex cursor-pointer items-center justify-between rounded px-2.5 py-1.5 text-base',
											{ 'bg-gray-100': active },
										]"
									>
										<div class="flex flex-1 gap-2 overflow-hidden">
											<div
												v-if="$slots['item-prefix'] || $props.multiple"
												class="flex-shrink-0"
											>
												<slot
													name="item-prefix"
													v-bind="{ active, selected, option }"
												>
													<Square
														v-if="!isOptionSelected(option)"
														class="h-4 w-4 text-gray-700"
													/>
													<CheckSquare
														v-else
														class="h-4 w-4 text-gray-700"
													/>
												</slot>
											</div>
											<span class="flex-1 truncate">
												{{ getLabel(option) }}
											</span>
										</div>

										<div
											v-if="$slots['item-suffix'] || option?.description"
											class="ml-2 flex-shrink-0"
										>
											<slot
												name="item-suffix"
												v-bind="{ active, selected, option }"
											>
												<div
													v-if="option?.description"
													class="text-sm text-gray-600"
												>
													{{ option.description }}
												</div>
											</slot>
										</div>
									</li>
								</ComboboxOption>
							</div>
							<li
								v-if="groups.length == 0"
								class="rounded-md px-2.5 py-1.5 text-base text-gray-600"
							>
								No results found
							</li>
						</ComboboxOptions>

						<div v-if="$slots.footer || multiple" class="border-t p-1">
							<slot name="footer" v-bind="{ togglePopover }">
								<div v-if="multiple" class="flex items-center justify-end">
									<Button
										v-if="!areAllOptionsSelected"
										label="Select All"
										@click.stop="selectAll"
									/>
									<Button
										v-if="areAllOptionsSelected"
										label="Clear All"
										@click.stop="clearAll"
									/></div
							></slot>
						</div>
					</div>
				</div>
			</template>
		</Popover>
	</Combobox>
</template>

<script>
import { fuzzySearch } from '@/utils'
import {
	Combobox,
	ComboboxButton,
	ComboboxInput,
	ComboboxOption,
	ComboboxOptions,
} from '@headlessui/vue'
import { CheckSquare, Square } from 'lucide-vue-next'
import { nextTick } from 'vue'
import Popover from '../Popover.vue'

export default {
	name: 'Autocomplete',
	props: [
		'modelValue',
		'options',
		'placeholder',
		'bodyClasses',
		'multiple',
		'returnValue',
		'hideSearch',
		'autoFocus',
	],
	emits: ['update:modelValue', 'update:query', 'change'],
	components: {
		Popover,
		Combobox,
		ComboboxInput,
		ComboboxOptions,
		ComboboxOption,
		ComboboxButton,
		CheckSquare,
		Square,
	},
	expose: ['togglePopover'],
	data() {
		return {
			query: '',
			showOptions: false,
		}
	},
	computed: {
		selectedValue: {
			get() {
				if (!this.multiple) {
					return this.findOption(this.modelValue)
				}
				// in case of `multiple`, modelValue is an array of values
				// and if returnValue is true, we need to return the value of the options
				return this.returnValue || typeof this.modelValue?.[0] !== 'object'
					? this.modelValue?.map((v) => this.findOption(v))
					: this.modelValue
			},
			set(val) {
				this.query = ''
				if (val && !this.multiple) this.showOptions = false
				if (!this.multiple) {
					this.$emit('update:modelValue', this.returnValue ? val?.value : val)
					return
				}
				this.$emit('update:modelValue', this.returnValue ? val?.map((v) => v.value) : val)
			},
		},
		groups() {
			if (!this.options || this.options.length == 0) return []

			let groups = this.options[0]?.group
				? this.options
				: [{ group: '', items: this.sanitizeOptions(this.options) }]

			return groups
				.map((group, i) => {
					return {
						key: i,
						group: group.group,
						hideLabel: group.hideLabel || false,
						items: this.filterOptions(this.sanitizeOptions(group.items)),
					}
				})
				.filter((group) => group.items.length > 0)
		},
		allOptions() {
			return this.groups.flatMap((group) => group.items)
		},
		areAllOptionsSelected() {
			if (!this.multiple) return false
			return this.allOptions.length === this.selectedValue?.length
		},
	},
	watch: {
		query(q) {
			this.$emit('update:query', q)
		},
		showOptions(val) {
			if (val) nextTick(() => this.$refs.searchInput?.$el?.focus())
		},
	},
	methods: {
		togglePopover(val) {
			this.showOptions = val ?? !this.showOptions
		},
		findOption(option) {
			if (!option) return option
			return this.allOptions.find((o) => o.value === (option.value || option))
		},
		filterOptions(options) {
			if (!this.query) return options
			return fuzzySearch(options, {
				term: this.query,
				keys: ['label', 'value'],
			})
		},
		displayValue(option) {
			if (!option) return ''

			if (!this.multiple) {
				if (typeof option === 'object') {
					return this.getLabel(option)
				}
				let selectedOption = this.allOptions.find((o) => o.value === option)
				return this.getLabel(selectedOption)
			}

			if (!Array.isArray(option)) return ''

			// in case of `multiple`, option is an array of values
			// so the display value should be comma separated labels
			return option
				.map((v) => {
					if (typeof v === 'object') {
						return this.getLabel(v)
					}
					let selectedOption = this.allOptions.find((o) => o.value === v)
					return this.getLabel(selectedOption)
				})
				.join(', ')
		},
		getLabel(option) {
			if (typeof option !== 'object') return option
			return option?.label || option?.value || 'No label'
		},
		sanitizeOptions(options) {
			if (!options) return []
			// in case the options are just strings, convert them to objects
			return options.map((option) => {
				return typeof option === 'object' ? option : { label: option, value: option }
			})
		},
		isOptionSelected(option) {
			if (!this.multiple) {
				return this.selectedValue?.value === option.value
			}
			return this.selectedValue?.find((v) => v && v.value === option.value)
		},
		selectAll() {
			this.selectedValue = this.allOptions
		},
		clearAll() {
			this.selectedValue = []
		},
	},
}
</script>
