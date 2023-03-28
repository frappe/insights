<script setup>
const props = defineProps({ link: { type: String, required: true } })
function openLink() {
	window.open(props.link, '_blank')
}
</script>

<template>
	<div class="relative">
		<slot></slot>
		<div
			v-if="props.link"
			class="absolute top-0 right-0 flex h-full w-8 cursor-pointer items-center justify-center"
			@click.prevent.stop="openLink"
		>
			<FeatherIcon name="link-2" class="h-4 w-4 text-gray-600 hover:text-gray-800" />
		</div>
	</div>
</template>
