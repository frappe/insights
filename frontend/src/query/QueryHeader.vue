<script setup lang="jsx">
import EditableTitle from '@/query/EditableTitle.vue'
import QueryMenu from '@/query/QueryMenu.vue'
import { inject } from 'vue'

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
	<div class="mr-2 flex h-full items-center space-x-2">
		<EditableTitle :title="query.doc.title" @update="updateTitle" />
		<QueryMenu />
	</div>
</template>
