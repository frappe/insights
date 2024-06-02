<script setup lang="ts">
import { inject } from 'vue'
import FiltersSelector from './FiltersSelector.vue'
import { Query } from '../query'

const emit = defineEmits({ select: (filters: FilterArgs[]) => true })
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
