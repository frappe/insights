<template>
	<div class="text-base text-gray-800">
		<div
			class="group flex items-baseline py-1 text-sm font-medium"
			:class="{ 'pl-1': level != 1 }"
		>
			<span
				class="mr-1 flex cursor-pointer items-center border-gray-200 group-hover:underline"
				@click="$emit('toggle_group_operator', { level })"
			>
				{{ group_operator }}
			</span>
			<span class="text-xs font-light text-gray-500">
				of the following are true
			</span>
		</div>
		<ul v-if="conditions && conditions.length" class="flex flex-col pl-4">
			<li
				v-for="(condition, idx) in conditions"
				:key="idx"
				class="list-disc marker:text-gray-400"
			>
				<div v-if="condition.group_operator" class="flex items-center">
					<FilterNode
						:filters="condition"
						@toggle_group_operator="
							(params) => $emit('toggle_group_operator', params)
						"
						@add_filter="(params) => $emit('add_filter', params)"
						@remove_filter="(params) => $emit('remove_filter', params)"
					/>
				</div>
				<div
					v-else
					class="group menu-item flex w-fit cursor-pointer items-center"
					@click="menu_open_for = idx"
				>
					<div class="flex h-8 items-center rounded px-1">
						<div class="pr-1 font-medium">{{ condition.left_label }}</div>
						<div class="pr-1 pt-0.5 text-xs font-light">
							{{ condition.operator }}
						</div>
						<div class="font-medium text-green-600">
							{{ condition.right_label }}
						</div>
						<div
							class="relative flex cursor-pointer items-center rounded py-1 pl-4 text-sm"
						>
							<MenuIcon
								class="group-hover:visible"
								:class="{
									visible: menu_open_for == idx,
									invisible: menu_open_for !== idx,
								}"
							/>
							<!-- Hidden Menu -->
							<transition
								enter-active-class="transition ease-out duration-100"
								enter-from-class="transform opacity-0 scale-95"
								enter-to-class="transform opacity-100 scale-100"
								leave-active-class="transition ease-in duration-100"
								leave-from-class="transform opacity-100 scale-100"
								leave-to-class="transform opacity-0 scale-95"
							>
								<div
									v-if="menu_open_for == idx"
									class="absolute left-4 top-6 z-10 origin-top-left rounded bg-white shadow-md ring-1 ring-gray-200"
								>
									<div
										v-for="(item, menu_item_idx) in menu_items"
										:key="menu_item_idx"
										class="cursor-pointer whitespace-nowrap px-3 py-1"
										:class="
											item.is_header
												? 'cursor-default border-b border-gray-200 text-xs font-light text-gray-500'
												: item.is_danger_action
												? 'border-t border-gray-200 text-red-400 hover:bg-gray-50'
												: item.is_chain_condition
												? 'font-light hover:bg-gray-50'
												: ''
										"
										@click.prevent.stop="on_menu_item_select(item, level, idx)"
									>
										{{ item.label }}
									</div>
								</div>
							</transition>
						</div>
					</div>
				</div>
			</li>
		</ul>
	</div>
</template>

<script>
import MenuIcon from './MenuIcon.vue'

export default {
	name: 'FilterNode',
	props: ['filters'],
	components: {
		MenuIcon,
	},
	data() {
		return {
			menu_open_for: null,
			menu_items: [
				{ label: 'Chain', is_header: true },
				{ label: 'And Condition', is_chain_condition: true },
				{ label: 'Or Condition', is_chain_condition: true },
				{ label: 'Remove', is_danger_action: true },
			],
		}
	},
	mounted() {
		// detect outside click to close menu
		document.addEventListener('click', (e) => {
			if (e.target.closest('.menu-item')) return
			this.menu_open_for = undefined
		})
	},
	computed: {
		level() {
			return this.filters.level || 1
		},
		group_operator() {
			return this.filters.group_operator || 'All'
		},
		conditions() {
			return this.filters.conditions || []
		},
	},
	methods: {
		on_menu_item_select(item, level, idx) {
			if (item.is_header) {
				return
			} else if (item.is_chain_condition) {
				this.$emit('add_filter', {
					idx,
					level,
					chain_operator: item.label.toLowerCase().split(' ')[0],
				})
			} else if (item.is_danger_action) {
				this.$emit('remove_filter', { idx, level })
			}
			this.menu_open_for = null
		},
	},
}
</script>
