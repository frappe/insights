<script setup lang="ts">
import { inject } from 'vue'
import { Query } from '../query'
import FiltersSelector from './FiltersSelector.vue'

const emit = defineEmits({ select: (args: FilterGroupArgs) => true })
const showDialog = defineModel()
const query = inject('query') as Query
</script>

<template>
	<Dialog :modelValue="showDialog" :options="{ size: '2xl' }">
		<template #body>
			<FiltersSelector
				:columnOptions="query.result.columnOptions"
				:columnValuesProvider="query.getDistinctColumnValues"
				@select="emit('select', $event)"
				@close="showDialog = false"
			/>
		</template>
	</Dialog>
</template>
