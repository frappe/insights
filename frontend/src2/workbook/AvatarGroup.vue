<script setup lang="ts">
import { Avatar } from 'frappe-ui'

const props = defineProps<{
	avatars: {
		image?: string
		label?: string
		size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl' | '2xl' | '3xl'
		shape?: 'circle' | 'square'
	}[]
}>()
</script>

<template>
	<div class="flex -space-x-2">
		<Avatar
			class="outline outline-2 outline-white"
			v-for="(avatar, idx) in avatars"
			:key="idx"
			v-bind="avatar"
		/>
	</div>
</template>
