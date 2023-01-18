<template>
	<div class="flex -space-x-2">
		<Avatar
			class="ring-2 ring-white"
			v-for="avatar in avatars"
			:key="avatar.label"
			:label="avatar.label"
			:imageURL="avatar.imageURL"
		/>
	</div>
</template>

<script setup>
const props = defineProps({
	avatars: {
		type: Array,
		required: true,
	},
})
</script>
