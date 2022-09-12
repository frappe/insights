<script setup>
import { inject, ref } from 'vue'
import QueryMenu from '@/components/Query/QueryMenu.vue'

const $notify = inject('$notify')
const query = inject('query')
const editTitle = ref(false)

const updateTitle = () => {
	if (!query.doc.title || query.doc.title.length == 0) {
		// TODO: restore old title without fetching the doc again
		// (?) create a local cache of the old document and compare it to the new one
		return query.reload.submit()
	}
	editTitle.value = false
	query.setValue.submit({ title: query.doc.title }).then(() => {
		$notify({
			title: 'Query title updated',
			appearance: 'success',
		})
	})
}
</script>

<template>
	<div class="flex items-center space-x-2">
		<div v-if="!editTitle" class="mr-2 py-1 text-3xl font-medium">
			{{ query.doc.title }}
		</div>
		<Button
			v-if="!editTitle"
			icon="edit"
			appearance="minimal"
			@click="
				() => {
					editTitle = true
					$nextTick(() => $refs.titleInput.$el.focus())
				}
			"
		></Button>
		<Input
			v-if="editTitle"
			ref="titleInput"
			type="text"
			v-model="query.doc.title"
			class="text-3xl font-medium"
		/>
		<Button v-if="editTitle" icon="x" @click="() => (editTitle = false)"></Button>
		<Button v-if="editTitle" icon="check" appearance="primary" @click="updateTitle()"></Button>
		<QueryMenu v-if="!editTitle" />
	</div>
</template>
