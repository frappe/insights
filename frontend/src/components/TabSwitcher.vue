<template>
	<div class="flex space-x-4 text-gray-500">
		<div
			v-for="(tab, i) in tabs"
			:key="i"
			class="flex w-fit items-center justify-center border-b-2 border-transparent px-1 py-2 text-lg"
			:class="{ 'border-blue-500 text-gray-600': active_tab === tab }"
			@click="
				() => {
					active_tab = tab
					$emit('tab_switched', tab)
				}
			"
		>
			{{ tab }}
		</div>
	</div>
</template>

<script>
export default {
	name: 'TabSwitcher',
	props: ['tabs'],
	emits: ['tab_switched'],
	data() {
		return {
			active_tab: this.tabs[0],
		}
	},
}
</script>
