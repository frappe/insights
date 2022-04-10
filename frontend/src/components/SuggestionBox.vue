<template>
	<transition
		enter-active-class="transition ease-out duration-100"
		enter-from-class="transform opacity-0 scale-95"
		enter-to-class="transform opacity-100 scale-100"
		leave-active-class="transition ease-in duration-75"
		leave-from-class="transform opacity-100 scale-100"
		leave-to-class="transform opacity-0 scale-95"
	>
		<div
			v-if="suggestions.length != 0"
			class="z-50 mt-2 max-h-48 w-fit min-w-[12rem] origin-top overflow-scroll overflow-x-hidden rounded-md bg-white shadow-md ring-1 ring-black ring-opacity-5 focus:outline-none"
		>
			<div
				v-for="(suggestion, idx) in suggestions"
				:key="idx"
				class="filter-picker-suggestion flex h-8 cursor-default items-center justify-between text-sm text-gray-700"
				:class="{
					'sticky top-0 h-6 rounded-none border-b border-gray-200 bg-white px-2': suggestion.is_header,
					'h-8 px-4 hover:bg-gray-100 hover:text-gray-900': !suggestion.is_header,
				}"
				@click.prevent.stop="!suggestion.is_header && $emit('select', suggestion)"
			>
				<div v-if="suggestion.is_header" class="flex items-center text-xs font-light text-gray-500">
					{{ suggestion.label }}
				</div>
				<div v-if="!suggestion.is_header" class="flex items-center whitespace-nowrap font-medium">
					<FeatherIcon v-if="suggestion.icon" :name="suggestion.icon" class="mr-2 h-3 w-3 text-gray-500" />
					{{ suggestion.label }}
				</div>
				<div v-if="suggestion.secondary_label" class="ml-4 flex whitespace-nowrap font-light text-gray-500">
					{{ suggestion.secondary_label }}
				</div>
			</div>
		</div>
	</transition>
</template>

<script>
export default {
	props: ['suggestions'],
}
</script>
