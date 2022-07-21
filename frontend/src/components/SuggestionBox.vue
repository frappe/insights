<template>
	<div
		class="mt-0 rounded-md rounded-t-none border border-t-0 bg-white shadow focus:outline-none"
	>
		<div class="max-h-48 origin-top overflow-scroll overflow-x-hidden p-1">
			<div
				v-for="(suggestion, idx) in suggestions"
				ref="suggestions"
				:key="idx"
				class="flex h-9 cursor-pointer items-center rounded px-3 text-base text-gray-600"
				:class="{
					'bg-gray-100 text-gray-800': active_suggestion_idx === idx,
				}"
				@mouseenter="active_suggestion_idx = idx"
				@click.prevent.stop="$emit('option-select', suggestion)"
			>
				<div class="mr-4 flex items-center overflow-hidden whitespace-nowrap font-medium">
					<FeatherIcon
						v-if="suggestion.icon"
						:name="suggestion.icon"
						class="mr-2 h-3 w-3 flex-shrink-0 text-gray-500"
					/>
					{{ suggestion.label }}
				</div>
				<div
					v-if="suggestion.description"
					class="ml-auto flex flex-shrink-0 whitespace-nowrap font-light text-gray-500"
				>
					{{ suggestion.description }}
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	props: ['suggestions', 'width'],
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
				const suggestion = this.suggestions[this.active_suggestion_idx || 0]
				if (suggestion) {
					this.$emit('option-select', suggestion)
				}
			}
		},
	},
}
</script>
