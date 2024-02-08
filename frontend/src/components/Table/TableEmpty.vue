<script setup>
import { PackageOpen } from 'lucide-vue-next'
</script>

<template>
	<div
		class="absolute top-0 flex h-full w-full flex-col items-center justify-center gap-2 text-base text-gray-500"
	>
		<PackageOpen class="h-12 w-12 text-gray-400" stroke-width="1" />
		<div class="text-center">No results to display</div>
	</div>
</template>
