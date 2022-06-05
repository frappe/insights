<template>
	<div class="relative flex w-full">
		<div class="z-10 flex w-full items-center">
			<div
				ref="group_operator"
				class="z-10 mr-2 flex h-6 w-6 flex-shrink-0 cursor-pointer items-center justify-center rounded-full border border-gray-300 bg-white font-light hover:border-blue-300 hover:font-medium hover:text-blue-500"
				@click.prevent.stop="$emit('toggle_group_operator', { level, position })"
			>
				{{ group_operator }}
			</div>
			<div class="flex flex-1 flex-col space-y-2">
				<div :key="idx" ref="condition" v-for="(condition, idx) in conditions">
					<div v-if="condition.group_operator">
						<FilterTree
							:filters="condition"
							@add_filter="$emit('add_filter', $event)"
							@edit_filter="$emit('edit_filter', $event)"
							@remove_filter="$emit('remove_filter', $event)"
							@branch_filter_at="$emit('branch_filter_at', $event)"
							@toggle_group_operator="$emit('toggle_group_operator', $event)"
						/>
					</div>
					<div
						v-else
						class="group relative flex h-9 w-fit cursor-pointer items-center rounded-md border px-2 hover:bg-gray-50"
						@click.prevent.stop="$emit('edit_filter', { level, position, idx })"
					>
						<div class="flex items-baseline space-x-2">
							<span class="flex items-baseline">{{ condition.left.label }} </span>
							<span class="flex items-baseline text-sm text-green-600"> {{ condition.operator.label }} </span>
							<span class="flex items-baseline">{{ condition.right.label }}</span>
						</div>
						<FeatherIcon
							name="x"
							class="ml-2 h-3 w-3 self-center text-gray-500 hover:text-gray-700"
							@click.prevent.stop="$emit('remove_filter', { level, position, idx })"
						/>
						<div
							class="invisible absolute flex h-full w-fit cursor-pointer items-center font-light text-gray-400 hover:visible hover:text-gray-500 group-hover:visible"
							:class="{
								'right-[-2.5rem] px-2': group_operator == '&',
								'right-[-3rem] px-1.5': group_operator == 'or',
							}"
							@click.prevent.stop="$emit('branch_filter_at', { level, position, idx })"
						>
							+ {{ group_operator == '&' ? 'or' : 'and' }}
						</div>
					</div>
				</div>
				<div
					ref="add_condition"
					class="!-mt-0.5 !-mb-2 flex h-9 cursor-pointer items-center text-sm font-light text-gray-400 hover:text-gray-500"
					@click.prevent.stop="$emit('add_filter', { level, position })"
				>
					+ {{ group_operator == '&' ? 'and' : 'or' }} condition
				</div>
			</div>
		</div>
		<div class="absolute top-0 left-0 z-0 h-full w-full">
			<svg width="100%" height="100%" class="text-gray-300">
				<g ref="connectors" fill="none"></g>
			</svg>
		</div>
	</div>
</template>

<script>
import { nextTick } from '@vue/runtime-core'

export default {
	name: 'FilterTree',
	props: ['filters'],
	data() {
		return {
			edit_filter_at: null,
		}
	},
	computed: {
		level() {
			return this.filters.level
		},
		position() {
			return this.filters.position
		},
		conditions() {
			return this.filters.conditions
		},
		group_operator() {
			return this.filters.group_operator
		},
	},
	watch: {
		filters: {
			handler() {
				nextTick(() => {
					this.draw_connectors()
				})
			},
			deep: true,
			immediate: true,
		},
	},
	methods: {
		draw_connectors() {
			this.$refs.connectors.innerHTML = ''
			this.$refs.condition.forEach((condition) => {
				this.add_connector(this.$refs.group_operator, condition)
			})
			this.add_connector(this.$refs.group_operator, this.$refs.add_condition, true)
		},
		add_connector(parent_node, child_node, dotted = false) {
			let path = document.createElementNS('http://www.w3.org/2000/svg', 'path')

			// we need to connect right side of the parent to the left side of the child node
			const pos_parent_center = {
				x: parent_node.offsetLeft + parent_node.offsetWidth / 2,
				y: parent_node.offsetTop + parent_node.offsetHeight / 2,
			}
			const pos_child_left = {
				x: child_node.offsetLeft,
				y: child_node.offsetTop + child_node.offsetHeight / 2,
			}

			const connector = this.get_connector(pos_parent_center, pos_child_left)

			path.setAttribute('d', connector)
			path.setAttribute('stroke', 'currentColor')
			if (dotted) {
				path.setAttribute('stroke-dasharray', '3,3')
			}

			this.$refs.connectors.appendChild(path)
		},
		get_connector(pos_parent_center, pos_child_left) {
			if (Math.abs(pos_parent_center.y - pos_child_left.y) < 3) {
				// don't add arcs if it's a straight line
				return `M${pos_parent_center.x},${pos_parent_center.y} L${pos_child_left.x},${pos_child_left.y}`
			} else {
				let arc_1 = ''
				let offset = 0

				if (pos_parent_center.y > pos_child_left.y) {
					// if child is above parent on Y axis 1st arc is anticlocwise
					// second arc is clockwise
					arc_1 = 'a5,5 0 0 1 5,-5 '
					offset = 5
				} else {
					// if child is below parent on Y axis 1st arc is clockwise
					// second arc is anticlockwise
					arc_1 = 'a5,5 1 0 0 5,5 '
					offset = -5
				}

				return (
					`M${pos_parent_center.x},${pos_parent_center.y} ` +
					`L${pos_parent_center.x},${pos_child_left.y + offset} ` +
					`${arc_1}` +
					`L${pos_child_left.x},${pos_child_left.y}`
				)
			}
		},
	},
}
</script>
