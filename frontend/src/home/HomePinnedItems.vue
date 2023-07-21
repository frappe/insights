<script setup>
import { ref } from 'vue'
const showNewPinDialog = ref(false)
</script>

<template>
	<div>
		<div class="flex items-center space-x-2">
			<div class="rounded bg-gray-100 p-1">
				<FeatherIcon name="bookmark" class="h-4 w-4" />
			</div>
			<div class="text-lg">Pinned Charts</div>
		</div>
		<div class="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4">
			<div
				class="col-span-1 flex cursor-pointer items-center space-x-2 rounded border border-dashed bg-gray-50 p-4 transition-all hover:border-gray-400"
				@click="showNewPinDialog = true"
			>
				<div class="rounded p-1">
					<FeatherIcon name="plus" class="h-4 w-4 text-gray-600" />
				</div>
				<div class="text-lg text-gray-600">Select a chart</div>
			</div>
		</div>
	</div>
	<Dialog v-model="showNewPinDialog">
		<!-- show a coming soon message for now -->
		<template #body>
			<div class="flex flex-col items-center justify-center space-y-4 p-6">
				<div class="h-72 w-full rounded bg-gray-200"></div>
				<div class="">Coming soon!</div>
			</div>
		</template>
	</Dialog>
</template>
