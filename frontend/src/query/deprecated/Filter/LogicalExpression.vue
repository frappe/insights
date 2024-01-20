<template>
	<div class="relative flex w-full">
		<div class="z-[5] flex w-full items-center">
			<div
				ref="operatorRef"
				class="z-[5] mr-2 flex h-6 w-6 flex-shrink-0 cursor-pointer items-center justify-center rounded-full border border-gray-300 bg-white hover:border-blue-300 hover:font-normal hover:text-blue-500"
				@click.prevent.stop="$emit('toggle-operator', { level, position })"
			>
				{{ operator == '&&' ? '&' : 'or' }}
			</div>
			<div class="flex flex-1 flex-col space-y-2">
				<div :key="idx" ref="conditionRefs" v-for="(condition, idx) in conditions">
					<LogicalExpression
						v-if="condition.type == 'LogicalExpression'"
						:expression="condition"
						@add-filter="$emit('add-filter', $event)"
						@edit-filter="$emit('edit-filter', $event)"
						@remove-filter="$emit('remove-filter', $event)"
						@toggle-operator="$emit('toggle-operator', $event)"
					/>
					<Expression
						v-else
						:expression="condition"
						@edit="
							$emit('edit-filter', {
								condition,
								level,
								position,
								idx,
							})
						"
						@remove="$emit('remove-filter', { level, position, idx })"
					/>
				</div>
				<div
					ref="addConditionRef"
					class="!-mt-0.5 !-mb-2 flex h-9 cursor-pointer items-center text-sm text-gray-600 hover:text-gray-700"
					@click.prevent.stop="$emit('add-filter', { level, position })"
				>
					+ {{ operator == '&&' ? 'and' : 'or' }} condition
				</div>
			</div>
		</div>
		<div class="absolute top-0 left-0 z-0 h-full w-full">
			<svg width="100%" height="100%" class="text-gray-400">
				<g ref="connectorsRef" fill="none"></g>
			</svg>
		</div>
	</div>
</template>

<script setup>
import { computed, nextTick, watch, ref, onMounted } from 'vue'
import Expression from './Expression.vue'

defineEmits(['add-filter', 'edit-filter', 'remove-filter', 'toggle-operator'])
const props = defineProps({
	expression: {
		type: Object,
		required: true,
		validate: (value) => value.type === 'LogicalExpression',
	},
})

const level = computed(() => props.expression.level)
const position = computed(() => props.expression.position)
const operator = computed(() => props.expression.operator)
const conditions = computed(() => props.expression.conditions)

onMounted(() => {
	watch(
		() => props.expression,
		() => nextTick(() => draw_connectors()),
		{
			immediate: true,
			deep: true,
		}
	)
})

const operatorRef = ref(null)
const addConditionRef = ref(null)
const connectorsRef = ref(null)
const conditionRefs = ref([])

function draw_connectors() {
	if (
		!connectorsRef.value ||
		!addConditionRef.value ||
		!operatorRef.value ||
		!conditionRefs.value?.length
	) {
		return
	}
	connectorsRef.value.innerHTML = ''
	conditionRefs.value.forEach((condition) => {
		add_connector(operatorRef.value, condition)
	})
	add_connector(operatorRef.value, addConditionRef.value, true)
}
function add_connector(parent_node, child_node, dotted = false) {
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

	const connector = get_connector(pos_parent_center, pos_child_left)

	path.setAttribute('d', connector)
	path.setAttribute('stroke', 'currentColor')
	if (dotted) {
		path.setAttribute('stroke-dasharray', '3,3')
	}

	connectorsRef.value.appendChild(path)
}
function get_connector(pos_parent_center, pos_child_left) {
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
}
</script>
