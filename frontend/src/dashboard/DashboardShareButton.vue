<script setup>
import ShareDialog from '@/components/ShareDialog.vue'
import { inject, ref } from 'vue'

const dashboard = inject('dashboard')
const showShareDialog = ref(false)
</script>

<template>
	<Button icon="share-2" appearance="white" @click="showShareDialog = true"> Share </Button>

	<ShareDialog
		v-if="dashboard.doc"
		v-model:show="showShareDialog"
		:resource-type="dashboard.doc.doctype"
		:resource-name="dashboard.doc.name"
	/>
</template>
