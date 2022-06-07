<template>
	<div class="flex space-x-3 border-b font-light text-gray-500">
		<div
			v-for="(tab, i) in tabs"
			:key="i"
			class="flex h-8 w-fit cursor-pointer justify-center px-1 text-lg"
			:class="{ 'border-b-2 border-blue-500 font-normal text-gray-600': active_tab === tab }"
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
