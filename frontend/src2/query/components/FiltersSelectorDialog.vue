<script setup lang="ts">
import { ColumnOption, FilterGroupArgs } from '../../types/query.types'
import FiltersSelector from './FiltersSelector.vue'

const props = defineProps<{
	initialFilters?: FilterGroupArgs
	columnOptions: ColumnOption[]
}>()
const emit = defineEmits({ select: (args: FilterGroupArgs) => true })
const showDialog = defineModel()
</script>

<template>
	<Dialog :modelValue="showDialog" :options="{ size: '2xl' }">
		<template #body>
			<FiltersSelector
				:initialFilters="props.initialFilters"
				:columnOptions="props.columnOptions"
				@close="showDialog = false"
				@select="
					(args) => {
						emit('select', args)
						showDialog = false
					}
				"
			/>
		</template>
	</Dialog>
</template>
