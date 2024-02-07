<script setup></script>

<template>
	<Popover placement="bottom-start">
		<template #target="{ togglePopover }">
			<Button icon="more-horizontal" @click="togglePopover"></Button>
		</template>
		<template #body="{ togglePopover }">
			<div
				class="relative mt-1 max-h-[26rem] w-[16rem] overflow-y-auto rounded-lg bg-white p-3 text-base shadow-2xl"
			>
				<slot v-bind="{ togglePopover }"></slot>
			</div>
		</template>
	</Popover>
</template>
