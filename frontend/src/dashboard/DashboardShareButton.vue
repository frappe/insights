<script setup>
import ShareDialog from '@/components/ShareDialog.vue'
import { inject, ref } from 'vue'

const dashboard = inject('dashboard')
const showShareDialog = ref(false)
</script>

<template>
	<Badge v-if="dashboard.isPrivate" class="flex items-center text-xs" color="yellow">
		Private
	</Badge>

	<Button iconLeft="share-2" appearance="white" @click="showShareDialog = true"> Share </Button>

	<ShareDialog
		v-if="dashboard.doc"
		v-model:show="showShareDialog"
		:resource-type="dashboard.doc.doctype"
		:resource-name="dashboard.doc.name"
	/>
</template>
