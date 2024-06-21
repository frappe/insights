<script setup lang="ts">
import { computed, inject } from 'vue'
import { Query } from '../query'
import FiltersSelector from './FiltersSelector.vue'
import { FilterGroupArgs } from '../../types/query.types'

const emit = defineEmits({ select: (args: FilterGroupArgs) => true })
const showDialog = defineModel()
const query = inject('query') as Query

const columnOptions = computed(() =>
	query.result.columnOptions.map((c) => ({
		...c,
		query: query.doc.name,
	}))
)
</script>

<template>
	<Dialog :modelValue="showDialog" :options="{ size: '2xl' }">
		<template #body>
			<FiltersSelector
				:columnOptions="columnOptions"
				@select="emit('select', $event)"
				@close="showDialog = false"
			/>
		</template>
	</Dialog>
</template>
