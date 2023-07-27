<script setup>
import { inject } from 'vue'
const dashboard = inject('dashboard')
</script>

<template>
	<div class="flex flex-1 flex-col items-center justify-center space-y-1">
		<div class="text-base font-light text-gray-600">
			{{
				!dashboard.editing ? "You haven't added any charts." : 'Drag and drop charts here.'
			}}
		</div>
		<div
			v-if="!dashboard.editing"
			class="cursor-pointer text-sm font-light text-blue-500 hover:underline"
			@click="dashboard.edit"
		>
			Add a chart
		</div>
	</div>
</template>
