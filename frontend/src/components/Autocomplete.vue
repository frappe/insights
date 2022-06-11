<template>
	<div :id="id" class="relative z-10 w-full rounded-md shadow-sm">
		<Popover class="flex w-full [&>div:first-child]:w-full">
			<template #target="{ isOpen, togglePopover }">
				<input
					type="text"
					autocomplete="off"
					spellcheck="false"
					:value="modelValue?.label"
					ref="autocomplete_input"
					:placeholder="placeholder"
					@focus="togglePopover()"
					@input="
						(e) => {
							input_value = e.target.value
							$emit('update:modelValue', {
								label: input_value,
								value: input_value,
							})
						}
					"
					@keydown.esc.exact="togglePopover()"
					class="form-input block h-8 w-full select-none rounded-md placeholder-gray-500 placeholder:text-sm"
					:class="{
						'focus:rounded-b-none focus:border focus:border-gray-200 focus:bg-white focus:shadow':
							isOpen && options?.length && filtered_options?.length,
					}"
				/>
			</template>
			<template #body="{ isOpen, togglePopover }">
				<SuggestionBox
					v-if="isOpen && options?.length && filtered_options?.length"
					:header_and_suggestions="filtered_options"
					@option-select="
						(option) => {
							on_option_select(option)
							togglePopover()
						}
					"
				/>
			</template>
		</Popover>
	</div>
</template>

<script>
import SuggestionBox from '@/components/SuggestionBox.vue'

export default {
	name: 'Autocomplete',
	props: {
		id: {
			type: String,
			required: true,
		},
		modelValue: {
			type: Object,
			default: () => ({
				label: '',
				value: '',
			}),
		},
		placeholder: {
			type: String,
			default: '',
		},
		options: {
			type: Array,
			required: true,
		},
	},
	emits: ['focus', 'option-select', 'update:modelValue'],
	components: {
		SuggestionBox,
	},
	data() {
		return {
			input_value: '',
		}
	},
	mounted() {
		// detect click outside of input
		this.outside_click_listener = (e) => {
			if (e.target.closest(`#${this.id}`)) {
				return this.$refs.autocomplete_input?.focus()
			}
			this.show = false
		}
		document.addEventListener('click', this.outside_click_listener)
	},
	beforeDestroy() {
		document.removeEventListener('click', this.outside_click_listener)
	},
	computed: {
		filtered_options() {
			// filter out duplicates
			const _options = this.options?.filter((option, index, self) => {
				return self.findIndex((t) => t.value === option.value) === index
			})
			return this.input_value
				? _options.filter((o) => o.label.toLowerCase().includes(this.input_value.toLowerCase()))
				: _options
		},
	},
	methods: {
		on_option_select(suggestion) {
			this.$emit('update:modelValue', suggestion)
			this.$emit('option-select', suggestion)
		},
	},
}
</script>
