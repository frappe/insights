<template>
	<div class="text-base text-slate-800">
		<div class="flex items-center pb-1 text-sm font-medium">
			<span v-if="level != 1" class="pr-2 font-medium text-slate-300">
				&#8226;
			</span>
			<span
				class="mr-1 flex cursor-pointer items-center rounded border border-slate-200 px-2 py-1"
				@click="$emit('toggle_group_operator', { level })"
			>
				{{ group_operator }}
			</span>
			<span class="text-xs font-light text-slate-400">
				of the following are true
			</span>
		</div>
		<div v-if="conditions && conditions.length" class="flex flex-col">
			<div v-for="(condition, idx) in conditions" :key="idx" class="pl-4">
				<div v-if="condition.group_operator" class="flex items-center pb-1">
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
					class="menu-item flex w-fit cursor-pointer items-center pb-1"
					@click="menu_open_for = idx"
				>
					<div class="pr-2 font-medium text-slate-300">&#8226;</div>
					<div
						class="flex h-10 items-center rounded border border-slate-200 px-3"
					>
						<div class="pr-1 font-medium">{{ condition.left }}</div>
						<div class="pr-1 text-xs font-light">{{ condition.operator }}</div>
						<div class="font-medium text-green-600">{{ condition.right }}</div>
						<div class="flex items-center text-sm">
							<div class="relative cursor-pointer rounded py-1 pl-4">
								<MenuIcon />
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
										class="absolute left-4 top-6 z-10 origin-top-left rounded bg-white shadow-md ring-1 ring-slate-200"
									>
										<div
											v-for="(item, menu_item_idx) in menu_items"
											:key="menu_item_idx"
											class="cursor-pointer whitespace-nowrap px-3 py-1"
											:class="
												item.is_header
													? 'cursor-default border-b border-slate-200 text-xs font-light text-slate-400'
													: item.is_danger_action
													? 'border-t border-slate-200 text-red-400 hover:bg-slate-50'
													: item.is_chain_condition
													? 'font-light hover:bg-slate-50'
													: ''
											"
											@click.prevent.stop="
												on_menu_item_select(item, level, idx)
											"
										>
											{{ item.label }}
										</div>
									</div>
								</transition>
							</div>
						</div>
					</div>
				</div>
			</div>
		</div>
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
