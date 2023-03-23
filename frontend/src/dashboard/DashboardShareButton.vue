<script setup>
import ShareDialog from '@/components/ShareDialog.vue'
import { inject, ref, computed } from 'vue'

const dashboard = inject('dashboard')
const showShareDialog = ref(false)
const sharedWithCount = computed(() => dashboard.sharedWith?.length || 0)
</script>

<template>
	<Badge v-if="sharedWithCount == 0" class="flex items-center text-xs" color="yellow">
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
