<script setup lang="ts"></script>

<template>
	<div
		class="sticky top-0 z-10 flex w-full flex-shrink-0 items-center justify-between bg-white px-3 py-3 shadow-sm"
	>
		<router-link :to="{ path: '/' }">
			<img src="../assets/insights-logo-new.svg" alt="logo" class="h-8" />
		</router-link>
		<slot name="actions"></slot>
	</div>
</template>
