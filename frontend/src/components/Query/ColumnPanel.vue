<template>
	<div class="m-4 flex flex-1 flex-col">
		<div v-if="!addingColumn && !editingColumn" class="flex flex-1 flex-col">
			<div class="mb-4 flex items-center justify-between">
				<div class="text-lg font-medium">Dimension & Metrics</div>
				<Button icon="plus" @click="addingColumn = true"></Button>
			</div>
			<ColumnList
				@edit-column="(column) => ([editColumn, editingColumn] = [column, true])"
			></ColumnList>
		</div>
		<ColumnPicker v-if="addingColumn" @close="addingColumn = false" />
		<ColumnEditor v-if="editingColumn" @close="editingColumn = false" :column="editColumn" />
	</div>
</template>

<script setup>
import ColumnList from '@/components/Query/ColumnList.vue'
import ColumnPicker from '@/components/Query/ColumnPicker.vue'
import ColumnEditor from '@/components/Query/ColumnEditor.vue'

import { inject, ref } from 'vue'

const query = inject('query')
const addingColumn = ref(false)
const editColumn = ref({})
const editingColumn = ref(false)
</script>
