<template>
	<div class="flex h-full w-full flex-col bg-gray-50">
		<div class="flex h-14 items-center justify-between border-b bg-white px-3 shadow-sm">
			<slot name="navbar"></slot>
		</div>
		<div class="flex flex-1 overflow-hidden">
			<div class="flex flex-1">
				<slot name="content"></slot>
			</div>
			<div v-if="$slots.sidebar" class="flex flex-shrink-0 overflow-hidden">
				<slot name="sidebar"></slot>
			</div>
		</div>
	</div>
</template>
