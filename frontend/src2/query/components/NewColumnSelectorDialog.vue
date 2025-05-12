<script setup lang="ts">
import { computed, ref } from 'vue'
import { COLUMN_TYPES } from '../../helpers/constants'
import { ColumnDataType, ColumnOption, MutateArgs } from '../../types/query.types'
import { expression } from '../helpers'
import ExpressionEditor from './ExpressionEditor.vue'

const props = defineProps<{ mutation?: MutateArgs; columnOptions: ColumnOption[] }>()
const emit = defineEmits({ select: (column: MutateArgs) => true })
const showDialog = defineModel()

const columnTypes = COLUMN_TYPES.map((t) => t.value as ColumnDataType)

const newColumn = ref(
	props.mutation
		? {
				name: props.mutation.new_name,
				type: props.mutation.data_type,
				expression: props.mutation.expression.expression,
		  }
		: {
				name: 'new_column',
				type: columnTypes[0],
				expression: '',
		  }
)

const isValid = computed(() => {
	return newColumn.value.name && newColumn.value.type && newColumn.value.expression.trim()
})

function confirmCalculation() {
	if (!isValid.value) return
	emit('select', {
		new_name: newColumn.value.name.trim(),
		data_type: newColumn.value.type,
		expression: expression(newColumn.value.expression),
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
	<Dialog
		:modelValue="showDialog"
		@after-leave="resetNewColumn"
		@close="!newColumn.expression && (showDialog = false)"
	>
		<template #body>
			<div class="bg-white px-4 pb-6 pt-5 sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Create Column</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md">
					</Button>
				</div>
				<div class="flex flex-col gap-2">
					<ExpressionEditor
						v-model="newColumn.expression"
						:column-options="props.columnOptions"
					/>
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
							label="Confirm"
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
