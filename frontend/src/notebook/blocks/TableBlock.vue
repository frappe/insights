<script setup>
import { moveCaretToEnd } from '@/utils'
import { computed, ref } from 'vue'
import ContentEditable from '../ContentEditable.vue'
const emit = defineEmits(['change'])
const props = defineProps({
	block: { type: Object, required: true },
})
const data = computed(
	() =>
		props.block.data || [
			['', ''],
			['', ''],
		]
)

const cells = ref()
const currentCellIndex = ref([0, 0])
const focusCell = (i, j) => {
	currentCellIndex.value = [i, j]
	const $cell = cells.value[i * data.value[i].length + j]
	$cell?.$el?.focus()
	moveCaretToEnd($cell?.$el)
}
const focusPreviousCell = (direction, event) => {
	const [i, j] = currentCellIndex.value
	// return if we're at the first cell, to move to the previous "block"
	if (direction === 'vertical' && i === 0) return
	if (direction === 'horizontal' && j === 0) return

	event.preventDefault()
	event.stopPropagation()
	if (direction === 'vertical' && i > 0) focusCell(i - 1, j)
	if (direction === 'horizontal' && j > 0) focusCell(i, j - 1)
}
const focusNextCell = (direction, event) => {
	const [i, j] = currentCellIndex.value
	// return if we're at the last cell, to move to the next "block"
	if (direction === 'vertical' && i === data.value.length - 1) return
	if (direction === 'horizontal' && j === data.value[i].length - 1) return

	event.preventDefault()
	event.stopPropagation()
	if (direction === 'vertical' && i < data.value.length - 1) focusCell(i + 1, j)
	if (direction === 'horizontal' && j < data.value[i].length - 1) focusCell(i, j + 1)
}
</script>

<template>
	<div class="my-6 w-fit rounded border">
		<table
			class="border-collapse"
			@keydown.up.exact="focusPreviousCell('vertical', $event)"
			@keydown.down.exact="focusNextCell('vertical', $event)"
			@keydown.left.exact="focusPreviousCell('horizontal', $event)"
			@keydown.right.exact="focusNextCell('horizontal', $event)"
		>
			<tr
				v-for="(row, i) in data"
				:key="row"
				class="border-b border-gray-200 last:border-b-0"
			>
				<td
					v-for="(cell, j) in row"
					:key="cell"
					class="min-w-[10rem] border-r border-gray-200 p-2 last:border-r-0"
				>
					<ContentEditable
						ref="cells"
						:value="cell"
						@change="cell = $event"
						class="focusable min-h-[1.25rem]"
						@click.prevent.stop="focusCell(i, j)"
					>
					</ContentEditable>
				</td>
			</tr>
		</table>
	</div>
</template>
