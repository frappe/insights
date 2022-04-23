<template>
	<div
		class="mt-2 max-h-48 w-fit min-w-[16rem] origin-top overflow-scroll overflow-x-hidden rounded-md bg-white shadow-md ring-1 ring-black ring-opacity-5 focus:outline-none"
	>
		<div
			v-if="header"
			class="sticky top-0 flex h-6 cursor-default items-center justify-between border-b border-gray-200 bg-white px-2 py-1 text-sm font-light text-gray-500"
		>
			{{ header.label }}
		</div>
		<div
			v-for="(suggestion, idx) in suggestions"
			ref="suggestions"
			:key="idx"
			class="flex cursor-default items-center justify-between rounded text-base text-gray-600"
			:class="{
				'h-9 px-4 hover:bg-gray-50': active_suggestion_idx !== idx && !suggestion.is_header,
				'h-9 bg-blue-50 px-4 text-blue-400': active_suggestion_idx === idx && !suggestion.is_header,
			}"
			@click.prevent.stop="!suggestion.is_header && $emit('select', suggestion)"
		>
			<div class="flex items-center whitespace-nowrap font-medium">
				<FeatherIcon v-if="suggestion.icon" :name="suggestion.icon" class="mr-2 h-3 w-3 text-gray-500" />
				{{ suggestion.label }}
			</div>
			<div v-if="suggestion.secondary_label" class="ml-4 flex whitespace-nowrap font-light text-gray-500">
				{{ suggestion.secondary_label }}
			</div>
		</div>
	</div>
</template>

<script>
export default {
	props: ['header_and_suggestions'],
	data() {
		return {
			active_suggestion_idx: 0,
		}
	},
	mounted() {
		document.addEventListener('keydown', this.on_keydown_event)
	},
	unmounted() {
		document.removeEventListener('keydown', this.on_keydown_event)
	},
	beforeDestroy() {
		document.removeEventListener('keydown', this.on_keydown_event)
	},
	computed: {
		header() {
			return this.header_and_suggestions.find((suggestion) => suggestion.is_header)
		},
		suggestions() {
			return this.header_and_suggestions.filter((suggestion) => !suggestion.is_header)
		},
	},
	methods: {
		on_keydown_event(e) {
			if (!['ArrowUp', 'ArrowDown', 'Enter'].includes(e.key)) {
				return
			}

			e.preventDefault()
			e.stopPropagation()

			if (e.key === 'ArrowDown') {
				this.active_suggestion_idx++
				if (this.active_suggestion_idx >= this.suggestions.length) {
					this.active_suggestion_idx = this.suggestions.length - 1
				}
				this.$refs.suggestions[this.active_suggestion_idx].scrollIntoView({
					behavior: 'smooth',
					block: 'nearest',
				})
			}
			if (e.key === 'ArrowUp') {
				this.active_suggestion_idx--
				if (this.active_suggestion_idx < 0) {
					this.active_suggestion_idx = 0
				}
				this.$refs.suggestions[this.active_suggestion_idx].scrollIntoView({
					behavior: 'smooth',
					block: 'nearest',
				})
			}
			if (e.key === 'Enter') {
				const suggestion = this.suggestions[this.active_suggestion_idx]
				!suggestion.is_header && this.$emit('select', suggestion)
			}
		},
	},
}
</script>
