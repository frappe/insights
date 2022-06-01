<template>
	<div class="flex flex-1 flex-col px-4">
		<div class="mb-3 flex h-8 flex-shrink-0 items-center rounded-md bg-gray-100 px-4 text-gray-500">Add Filter</div>
		<div class="relative h-[calc(100%-3rem)] overflow-scroll">
			<div class="absolute top-0 left-0 h-full w-full">
				<svg ref="arrows" width="100%" height="100%" class="text-gray-300">
					<g ref="connectors" fill="none"></g>
				</svg>
			</div>
			<div class="flex items-center">
				<div
					ref="and"
					class="z-10 mr-1 flex h-6 w-6 items-center justify-center rounded-full border bg-white font-light"
				>
					&
				</div>
				<div class="flex flex-1 flex-col space-y-2">
					<div ref="first" class="flex h-8 w-fit items-center rounded-md border px-2 hover:bg-gray-50">
						<div class="flex items-baseline space-x-2">
							<span class="flex items-baseline">Fieldtype</span>
							<span class="flex items-baseline text-sm text-green-600">equals</span>
							<span class="flex items-baseline">Table</span>
						</div>
					</div>
					<div ref="second" class="flex h-8 w-fit items-center rounded-md border px-2 hover:bg-gray-50">
						<div class="flex items-baseline space-x-2">
							<span class="flex items-baseline">Fieldtype</span>
							<span class="flex items-baseline text-sm text-green-600">equals</span>
							<span class="flex items-baseline">Table</span>
						</div>
					</div>
					<div ref="third" class="flex w-fit items-center">
						<div
							ref="or"
							class="z-10 mr-1 flex h-6 w-6 items-center justify-center rounded-full border bg-white font-light"
						>
							or
						</div>
						<div class="flex flex-1 flex-col space-y-2">
							<div ref="or_first" class="flex h-8 w-fit items-center rounded-md border px-2 hover:bg-gray-50">
								<div class="flex items-baseline space-x-2">
									<span class="flex items-baseline">Fieldtype</span>
									<span class="flex items-baseline text-sm text-green-600">equals</span>
									<span class="flex items-baseline">Table</span>
								</div>
							</div>
							<div ref="or_second" class="flex h-8 w-fit items-center rounded-md border px-2 hover:bg-gray-50">
								<div class="flex items-baseline space-x-2">
									<span class="flex items-baseline">Fieldtype</span>
									<span class="flex items-baseline text-sm text-green-600">equals</span>
									<span class="flex items-baseline">Table</span>
								</div>
							</div>
							<div ref="or_third" class="w-fit text-sm font-light text-gray-500/70">+ or condition</div>
						</div>
					</div>
					<div ref="fourth" class="w-fit text-sm font-light text-gray-500/70">+ and condition</div>
				</div>
			</div>
		</div>
	</div>
</template>

<script>
export default {
	name: 'FilterPicker',
	mounted() {
		const and = this.$refs.and
		const first = this.$refs.first
		const second = this.$refs.second
		const third = this.$refs.third
		this.add_connector(and, first)
		this.add_connector(and, second)
		this.add_connector(and, third)
		this.add_connector(and, this.$refs.fourth, true)

		this.add_connector(this.$refs.or, this.$refs.or_first)
		this.add_connector(this.$refs.or, this.$refs.or_second)
		this.add_connector(this.$refs.or, this.$refs.or_third, true)
	},
	methods: {
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
