<template>
	<div class="flex -space-x-2">
		<Avatar
			class="border-2 border-white"
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
