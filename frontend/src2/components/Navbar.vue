<script setup lang="ts"></script>

<template>
	<div
		class="sticky top-0 z-10 flex w-full flex-shrink-0 items-center gap-3 bg-white px-3 py-2 shadow-sm"
	>
		<router-link :to="{ path: '/' }">
			<img src="../assets/insights-logo-new.svg" alt="logo" class="h-8" />
		</router-link>
		<div class="flex flex-1 items-center justify-between">
			<div>
				<slot name="left"></slot>
			</div>
			<div>
				<slot name="actions"></slot>
			</div>
		</div>
	</div>
</template>
