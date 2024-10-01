<script setup lang="ts">
import { ColumnOption, FilterGroupArgs, GroupedColumnOption } from '../../types/query.types'
import FiltersSelector from './FiltersSelector.vue'

const props = defineProps<{
	filterGroup?: FilterGroupArgs
	columnOptions: ColumnOption[] | GroupedColumnOption[]
}>()
const emit = defineEmits({ select: (args: FilterGroupArgs) => true })
const showDialog = defineModel()
</script>

<template>
	<Dialog v-model="showDialog" :options="{ size: '2xl' }">
		<template #body>
			<FiltersSelector
				:filterGroup="props.filterGroup"
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
