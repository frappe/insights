<template>
	<div class="flex space-x-1 border-b font-light text-gray-500">
		<div
			v-for="(tab, i) in tabs"
			:key="i"
			class="relative flex h-8 w-fit cursor-pointer justify-center px-2 text-lg"
			:class="{
				'border-b-2 border-blue-500 font-normal text-gray-600':
					props.activeTab == tab.label,
				'cursor-not-allowed': tab.disabled,
			}"
			@click="$emit('tab-switched', tab)"
		>
			{{ tab.label }}
			<span
				v-if="tab.showIndicator"
				class="absolute -top-1 right-0 h-1.5 w-1.5 rounded-full bg-red-500"
			></span>
		</div>
	</div>
</template>

<script setup>
const props = defineProps({
	tabs: {
		type: Array,
		required: true,
	},
	activeTab: {
		type: String,
		default: '',
	},
})
defineEmits(['tab-switched'])
</script>
