<template>
	<div :id="id" class="relative z-10 w-full rounded-md shadow-sm">
		<Popover :show="input_focused">
			<template #target>
				<input
					type="text"
					autocomplete="off"
					spellcheck="false"
					:value="modelValue"
					ref="autocomplete_input"
					:placeholder="placeholder"
					@blur="$emit('blur', $event)"
					@focus="
						() => {
							input_focused = true
							$emit('focus', $event)
						}
					"
					@input="
						(e) => {
							input_value = e.target.value
							$emit('update:modelValue', e.target.value)
						}
					"
					class="form-input block h-8 w-full select-none rounded-md text-sm placeholder-gray-500 focus:rounded-b-none focus:border focus:border-gray-200 focus:bg-white focus:shadow"
				/>
			</template>
			<template #content>
				<SuggestionBox
					v-if="input_focused && options?.length && filtered_options?.length"
					:header_and_suggestions="filtered_options"
					@select="on_option_select"
				/>
			</template>
		</Popover>
	</div>
</template>

<script>
import SuggestionBox from '@/components/SuggestionBox.vue'

export default {
	props: ['id', 'modelValue', 'placeholder', 'options'],
	emits: ['focus', 'blur', 'select', 'update:modelValue'],
	components: {
		SuggestionBox,
	},
	data() {
		return {
			input_value: '',
			input_focused: false,
		}
	},
	mounted() {
		// detect click outside of input
		this.outside_click_listener = (e) => {
			if (e.target.closest(`#${this.id}`)) {
				return this.$refs.autocomplete_input?.focus()
			}
			this.input_focused = false
		}
		document.addEventListener('click', this.outside_click_listener)
	},
	beforeDestroy() {
		document.removeEventListener('click', this.outside_click_listener)
	},
	computed: {
		filtered_options() {
			return this.input_value
				? this.options.filter((o) => o.label.toLowerCase().includes(this.input_value.toLowerCase()))
				: this.options
		},
	},
	methods: {
		on_option_select(suggestion) {
			this.$emit('update:modelValue', suggestion.label)
			this.$emit('select', suggestion)
			this.reset()
		},
		reset() {
			this.$refs.autocomplete_input?.blur()
			this.input_focused = false
		},
	},
}
</script>
