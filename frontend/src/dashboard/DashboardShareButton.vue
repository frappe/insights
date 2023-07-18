<script setup>
import ShareDialog from '@/components/ShareDialog.vue'
import { inject, ref } from 'vue'

const dashboard = inject('dashboard')
const showShareDialog = ref(false)
</script>

<template>
	<Badge v-if="dashboard.isPrivate" theme="yellow"> Private </Badge>

	<Button variant="outline" @click="showShareDialog = true"> Share </Button>

	<ShareDialog
		v-if="dashboard.doc"
		v-model:show="showShareDialog"
		:resource-type="dashboard.doc.doctype"
		:resource-name="dashboard.doc.name"
		:allow-public-access="true"
		:isPublic="Boolean(dashboard.doc.is_public)"
		@togglePublicAccess="dashboard.togglePublicAccess"
	/>
</template>
