<script>
import QueryBlock from './QueryBlock.vue'
export default {
	inheritAttrs: false,
	components: { QueryBlock },
}
</script>

<template>
	<Suspense>
		<QueryBlock v-bind="{ ...$attrs, ...$props }" />
		<template #fallback>
			<div class="flex h-20 w-full flex-col items-center justify-center">
				<LoadingIndicator class="mb-2 w-6 text-gray-300" />
			</div>
		</template>
	</Suspense>
</template>
