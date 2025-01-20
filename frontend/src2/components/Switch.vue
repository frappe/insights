<template>
	<div class="flex h-7 w-full cursor-pointer select-none items-center rounded border bg-gray-100">
		<div
			v-for="tab in tabs"
			class="flex h-full flex-1 items-center justify-center truncate px-4 text-gray-700 transition-all"
			:class="{
				'rounded bg-white text-gray-800 shadow':
					tab.active ||
					currentTab === tab.value ||
					(currentTab === undefined && tab.default),
				'cursor-not-allowed': tab.disabled,
			}"
			@click="handleClick(tab)"
		>
			{{ tab.label }}
		</div>
	</div>
</template>

<script setup>
import { computed } from 'vue'

const currentTab = defineModel()
const emit = defineEmits(['switch'])
const props = defineProps({ tabs: { type: Array, required: true } })

const tabs = computed(() => {
	if (typeof props.tabs?.[0] == 'string') {
		return props.tabs.map((label) => ({ label, value: label }))
	}
	return props.tabs
})
function handleClick(tab) {
	if (tab.disabled) return
	currentTab.value = tab.value
	emit('switch', tab)
}
</script>
