<script setup lang="ts"></script>

<template>
	<div
		class="sticky top-0 z-10 flex w-full flex-shrink-0 items-center gap-3 bg-white px-3 py-2 shadow-sm"
	>
		<div class="flex flex-1 items-center justify-between">
			<div>
				<slot name="left">
					<router-link :to="{ path: '/' }">
						<img src="../assets/insights-logo-new.svg" alt="logo" class="h-8" />
					</router-link>
				</slot>
			</div>
			<div>
				<slot name="center"></slot>
			</div>
			<div>
				<slot name="right"></slot>
			</div>
		</div>
	</div>
</template>
