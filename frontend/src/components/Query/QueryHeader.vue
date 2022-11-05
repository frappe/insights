<script setup>
import { inject } from 'vue'
import QueryMenu from '@/components/Query/QueryMenu.vue'
import EditablePageTitle from '@/components/EditablePageTitle.vue'

const $notify = inject('$notify')
const query = inject('query')

const updateTitle = (title) => {
	if (!title || title === query.doc.title) return
	query.setValue.submit({ title }).then(() => {
		$notify({
			title: 'Query title updated',
			appearance: 'success',
		})
		query.doc.title = title
	})
}
</script>

<template>
	<div class="flex h-full items-center space-x-2">
		<EditablePageTitle :title="query.doc.title" @update="updateTitle" />
		<QueryMenu />
	</div>
</template>
