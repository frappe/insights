<script setup lang="ts">
import Code from '@/components/Controls/Code.vue'
import { COLUMN_TYPES } from '@/utils'
import { computed, ref } from 'vue'
import { expression } from './query_utils'

const emit = defineEmits({ select: (column: MutateArgs) => true })
const showDialog = defineModel()

const columnTypes = COLUMN_TYPES.map((t) => t.value as ColumnDataType)

const newColumn = ref({
	name: 'New Column',
	type: columnTypes[0],
	expression: '',
})

const isValid = computed(() => {
	return newColumn.value.name && newColumn.value.type && newColumn.value.expression
})

function confirmCalculation() {
	if (!isValid.value) return
	emit('select', {
		new_name: newColumn.value.name,
		data_type: newColumn.value.type,
		mutation: expression(newColumn.value.expression),
	})
	resetNewColumn()
	showDialog.value = false
}
function resetNewColumn() {
	newColumn.value = {
		name: 'New Column',
		type: columnTypes[0],
		expression: '',
	}
}
</script>

<template>
	<Dialog :modelValue="showDialog" @after-leave="resetNewColumn">
		<template #body>
			<div class="bg-white px-4 pb-6 pt-5 sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Create Column</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md">
					</Button>
				</div>
				<div class="flex flex-col gap-2">
					<div class="flex h-[14rem] w-full rounded border text-base">
						<Code
							class="column-expression"
							v-model="newColumn.expression"
							language="python"
						></Code>
					</div>
					<div class="flex gap-2">
						<FormControl
							type="text"
							class="flex-1"
							label="Column Name"
							autocomplete="off"
							placeholder="Column Name"
							v-model="newColumn.name"
						/>
						<FormControl
							type="select"
							class="flex-1"
							label="Column Type"
							autocomplete="off"
							:options="columnTypes"
							v-model="newColumn.type"
						/>
					</div>
				</div>
				<div class="mt-2 flex items-center justify-between gap-2">
					<div></div>
					<div class="flex items-center gap-2">
						<Button
							label="Add Column"
							variant="solid"
							:disabled="!isValid"
							@click="confirmCalculation"
						/>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<style lang="scss">
.column-expression {
	.cm-content {
		height: 14rem !important;
	}
	.cm-gutters {
		height: 14rem !important;
	}
}
</style>
