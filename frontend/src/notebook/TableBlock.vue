<script setup>
import { computed, ref } from 'vue'
import ContentEditable from './ContentEditable.vue'
const emit = defineEmits(['change'])
const props = defineProps({
	block: {
		type: Object,
		required: true,
	},
})
const contentEditable = ref()
</script>

<template>
	<div class="w-fit rounded border">
		<table class="border-collapse">
			<tr
				v-for="row in block.content"
				:key="row"
				class="border-b border-gray-200 last:border-b-0"
			>
				<td
					v-for="cell in row"
					:key="cell"
					class="min-w-[10rem] border-r border-gray-200 p-2 last:border-r-0"
				>
					<ContentEditable
						ref="contentEditable"
						:class="['min-h-[1.25rem]']"
						:value="cell"
						@change="cell = $event"
					>
					</ContentEditable>
				</td>
			</tr>
		</table>
	</div>
</template>
