<template>
	<div class="flex w-40 flex-col rounded border bg-white p-1 text-base shadow">
		<template v-if="enabledItems.length">
			<button
				class="flex h-8 w-full cursor-pointer items-center rounded px-1 text-base"
				:class="{ 'bg-gray-100': index === selectedIndex }"
				v-for="(item, index) in enabledItems"
				:key="index"
				@click="selectItem(index)"
				@mouseenter="selectedIndex = index"
			>
				<component :is="item.icon || 'Minus'" class="mr-2 h-4 w-4 text-gray-600" />
				{{ item.title }}
			</button>
		</template>
		<div class="item" v-else>No result</div>
	</div>
</template>

<script>
import { Minus } from 'lucide-vue-next'
export default {
	props: {
		items: {
			type: Array,
			required: true,
		},

		editor: {
			type: Object,
			required: true,
		},

		command: {
			type: Function,
			required: true,
		},
	},

	components: {
		Minus,
	},

	data() {
		return {
			selectedIndex: 0,
		}
	},

	watch: {
		items() {
			this.selectedIndex = 0
		},
	},

	computed: {
		enabledItems() {
			return this.items.filter((item) => (item.disabled ? !item.disabled(this.editor) : true))
		},
	},

	methods: {
		onKeyDown({ event }) {
			if (event.key === 'ArrowUp') {
				this.upHandler()
				return true
			}

			if (event.key === 'ArrowDown') {
				this.downHandler()
				return true
			}

			if (event.key === 'Enter') {
				this.enterHandler()
				return true
			}

			return false
		},

		upHandler() {
			this.selectedIndex =
				(this.selectedIndex + this.enabledItems.length - 1) % this.enabledItems.length
		},

		downHandler() {
			this.selectedIndex = (this.selectedIndex + 1) % this.enabledItems.length
		},

		enterHandler() {
			this.selectItem(this.selectedIndex)
		},

		selectItem(index) {
			const item = this.enabledItems[index]

			if (item) {
				this.command(item)
			}
		},
	},
}
</script>
