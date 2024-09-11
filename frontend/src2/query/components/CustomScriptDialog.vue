<script setup lang="ts">
import { computed, ref } from 'vue'
import { ColumnOption, CustomOperationArgs } from '../../types/query.types'
import { expression } from '../helpers'
import ExpressionEditor from './ExpressionEditor.vue'
import { copy } from '../../helpers'

const props = defineProps<{ operation?: CustomOperationArgs; columnOptions: ColumnOption[] }>()
const emit = defineEmits({ select: (operation: CustomOperationArgs) => true })
const showDialog = defineModel()

const newOperation = ref(
	props.operation
		? copy(props.operation)
		: {
				expression: expression(''),
		  }
)

const isValid = computed(() => {
	return newOperation.value.expression.expression.trim().length > 0
})

function confirm() {
	if (!isValid.value) return
	emit('select', newOperation.value)
	reset()
	showDialog.value = false
}
function reset() {
	newOperation.value = {
		expression: expression(''),
	}
}
</script>

<template>
	<Dialog
		:modelValue="showDialog"
		@after-leave="reset"
		@close="!newOperation.expression.expression && (showDialog = false)"
		:options="{ size: '4xl' }"
	>
		<template #body>
			<div class="bg-white px-4 pb-6 pt-5 sm:px-6">
				<div class="flex items-center justify-between pb-4">
					<h3 class="text-2xl font-semibold leading-6 text-gray-900">Custom Operation</h3>
					<Button variant="ghost" @click="showDialog = false" icon="x" size="md">
					</Button>
				</div>
				<div class="flex flex-col gap-2">
					<ExpressionEditor
						class="h-[26rem]"
						v-model="newOperation.expression.expression"
						:column-options="props.columnOptions"
					/>
				</div>
				<div class="mt-2 flex items-center justify-between gap-2">
					<div></div>
					<div class="flex items-center gap-2">
						<Button
							label="Confirm"
							variant="solid"
							:disabled="!isValid"
							@click="confirm"
						/>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
