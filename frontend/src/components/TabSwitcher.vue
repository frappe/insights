<template>
	<div class="flex space-x-3 font-light text-gray-500">
		<div
			v-for="(tab, i) in tabs"
			:key="i"
			class="flex h-8 w-fit justify-center border-b-2 border-transparent px-1 text-lg"
			:class="{ 'border-blue-500 font-normal text-gray-600': active_tab === tab }"
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
