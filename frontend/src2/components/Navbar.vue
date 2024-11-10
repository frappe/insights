<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()
</script>

<template>
	<div
		class="sticky top-0 z-10 flex h-11 w-full flex-shrink-0 items-center gap-3 bg-white px-3 shadow-sm"
	>
		<div class="relative flex flex-1 items-center">
			<div class="absolute left-0">
				<slot name="left">
					<button @click="router.back()" class="flex items-center gap-1">
						<img src="../assets/insights-logo-new.svg" alt="logo" class="h-7 rounded" />
					</button>
				</slot>
			</div>
			<div class="flex flex-1 items-center justify-center">
				<slot name="center"></slot>
			</div>
			<div class="absolute right-0">
				<slot name="right"></slot>
			</div>
		</div>
	</div>
</template>
