<script setup>
import { inject, ref, unref } from 'vue'
import QueryMenu from '@/components/Query/QueryMenu.vue'

const $notify = inject('$notify')
const query = inject('query')
const editTitle = ref(false)

const oldTitle = ref(unref(query).doc?.title)
const updateTitle = () => {
	if (!query.doc.title || query.doc.title.length == 0) {
		return (query.doc.title = oldTitle.value)
	}
	editTitle.value = false
	query.setValue.submit({ title: query.doc.title }).then(() => {
		$notify({
			title: 'Query title updated',
			appearance: 'success',
		})
	})
	oldTitle.value = query.doc.title
}
</script>

<template>
	<div class="flex h-full items-center space-x-2">
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
					oldTitle = query.doc.title
					$nextTick(() => $refs.titleInput.$el.focus())
				}
			"
		></Button>
		<Input
			v-if="editTitle"
			ref="titleInput"
			type="text"
			:value="query.doc.title"
			:size="query.doc.title.length + 1"
			@input="(val) => (query.doc.title = val)"
			class="text-3xl font-medium"
		/>
		<Button
			v-if="editTitle"
			icon="x"
			@click="
				() => {
					editTitle = false
					query.doc.title = oldTitle
				}
			"
		></Button>
		<Button v-if="editTitle" icon="check" appearance="primary" @click="updateTitle()"></Button>
		<QueryMenu v-if="!editTitle" />
	</div>
</template>
