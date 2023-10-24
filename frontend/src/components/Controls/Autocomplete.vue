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
							<div class="flex items-center overflow-hidden">
								<slot name="prefix" />
								<span class="truncate text-base leading-5" v-if="selectedValue">
									{{ displayValue(selectedValue) }}
								</span>
								<span class="text-base leading-5 text-gray-600" v-else>
									{{ placeholder || '' }}
								</span>
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
			<template #body="{ isOpen }">
				<div v-show="isOpen">
					<ComboboxOptions
						class="mt-1 max-h-[15rem] overflow-y-auto rounded-lg bg-white px-1.5 pb-1.5 shadow-2xl"
						:class="bodyClasses"
						static
					>
						<div
							class="sticky top-0 z-10 flex items-stretch space-x-1.5 bg-white pt-1.5"
						>
							<div class="relative w-full">
								<ComboboxInput
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
							class="mt-1.5"
							v-for="group in groups"
							:key="group.key"
							v-show="group.items.length > 0"
						>
							<div
								v-if="group.group && !group.hideLabel"
								class="px-2.5 py-1.5 text-sm font-medium text-gray-600"
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
									<div class="flex space-x-2">
										<slot
											name="item-prefix"
											v-bind="{ active, selected, option }"
										/>
										<span class="truncate">{{
											option?.label || option?.value || option || 'No label'
										}}</span>
									</div>
									<slot name="item-suffix" v-bind="{ active, selected, option }">
										<div
											v-if="option?.description"
											class="text-sm text-gray-600"
										>
											{{ option.description }}
										</div>
									</slot>
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
				</div>
			</template>
		</Popover>
	</Combobox>
</template>
<script>
import {
	Combobox,
	ComboboxButton,
	ComboboxInput,
	ComboboxOption,
	ComboboxOptions,
} from '@headlessui/vue'
import { Popover } from 'frappe-ui'

export default {
	name: 'Autocomplete',
	props: ['modelValue', 'options', 'placeholder', 'bodyClasses', 'multiple', 'returnValue'],
	emits: ['update:modelValue', 'update:query', 'change'],
	components: {
		Popover,
		Combobox,
		ComboboxInput,
		ComboboxOptions,
		ComboboxOption,
		ComboboxButton,
	},
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
					return this.returnValue ? this.findOption(this.modelValue) : this.modelValue
				}
				// in case of `multiple`, modelValue is an array of values
				// and if returnValue is true, we need to return the value of the options
				return this.returnValue
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
				: [{ group: '', items: this.options }]

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
	},
	watch: {
		query(q) {
			this.$emit('update:query', q)
		},
	},
	methods: {
		findOption(value) {
			return this.allOptions.find((o) => o.value === value)
		},
		filterOptions(options) {
			if (!this.query) return options
			return betterSearch(this.query, { items: options })
		},
		displayValue(option) {
			if (!this.multiple) {
				if (typeof option === 'object') {
					return option?.label
				}
				let selectedOption = this.allOptions.find((o) => o.value === option)
				return selectedOption?.label || option
			}

			// in case of `multiple`, option is an array of values
			// so the display value should be comma separated labels
			return option
				.map((v) => {
					if (typeof v === 'object') {
						return v?.label
					}
					let selectedOption = this.allOptions.find((o) => o.value === v)
					return selectedOption?.label || v
				})
				.join(', ')
		},
		sanitizeOptions(options) {
			// in case the options are just strings, convert them to objects
			return options.map((option) => {
				return typeof option === 'object' ? option : { label: option, value: option }
			})
		},
	},
}

function betterSearch(query, options) {
	const results = []
	const keysToSearch = options.keys || ['label', 'value']
	const queryWords = query.toLowerCase().split(' ')

	options.items.forEach((item) => {
		const itemWords = keysToSearch
			.map((key) => (item[key] || '').toLowerCase())
			.join(' ')
			.split(' ')

		const score = queryWords.reduce((acc, queryWord) => {
			const wordScore = itemWords.reduce((acc, itemWord) => {
				if (itemWord.startsWith(queryWord)) {
					return acc + 100
				}
				if (itemWord.includes(queryWord)) {
					return acc + 10
				}
				return acc
			}, 0)
			return acc + wordScore
		}, 0)

		if (score > 0) {
			results.push({ item, score })
		}
	})
	return results.sort((a, b) => b.score - a.score).map((result) => result.item)
}
</script>
