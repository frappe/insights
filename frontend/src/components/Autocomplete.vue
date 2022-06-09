<template>
	<div :id="id" class="relative z-10 w-full rounded-md shadow-sm">
		<Popover :show="show">
			<template #target>
				<input
					type="text"
					autocomplete="off"
					spellcheck="false"
					:value="modelValue?.label"
					ref="autocomplete_input"
					:placeholder="placeholder"
					@focus="
						() => {
							show = true
							$emit('focus', $event)
						}
					"
					@input="
						(e) => {
							input_value = e.target.value
							$emit('update:modelValue', {
								label: input_value,
								value: input_value,
							})
						}
					"
					@keydown.esc.exact="show = false"
					class="form-input block h-8 w-full select-none rounded-md placeholder-gray-500 placeholder:text-sm"
					:class="{
						'focus:rounded-b-none focus:border focus:border-gray-200 focus:bg-white focus:shadow':
							show && options?.length && filtered_options?.length,
					}"
				/>
			</template>
			<template #content>
				<SuggestionBox
					v-if="show && options?.length && filtered_options?.length"
					:header_and_suggestions="filtered_options"
					@option-select="on_option_select"
				/>
			</template>
		</Popover>
	</div>
</template>

<script>
import SuggestionBox from '@/components/SuggestionBox.vue'

export default {
	name: 'Autocomplete',
	// modelValue = { label, value } and options = [{ label, value }, ...]
	props: ['id', 'modelValue', 'placeholder', 'options'],
	emits: ['focus', 'option-select', 'update:modelValue'],
	components: {
		SuggestionBox,
	},
	data() {
		return {
			input_value: '',
			show: false,
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
			this.reset()
		},
		reset() {
			this.$refs.autocomplete_input?.blur()
			this.show = false
		},
	},
}
</script>
