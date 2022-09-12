<template>
	<div class="flex h-full w-1/3 flex-col overflow-scroll px-4 pb-4">
		<div v-if="!addingColumn && !editingColumn" class="flex flex-1 flex-col">
			<div class="sticky top-0 flex items-center justify-between bg-white pb-3 pt-1">
				<div class="text-sm tracking-wide text-gray-600">COLUMNS</div>
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
import ColumnList from '@/components/Query/Column/ColumnList.vue'
import ColumnPicker from '@/components/Query/Column/ColumnPicker.vue'
import ColumnEditor from '@/components/Query/Column/ColumnEditor.vue'

import { inject, ref } from 'vue'

const query = inject('query')
const addingColumn = ref(false)
const editColumn = ref({})
const editingColumn = ref(false)
</script>
