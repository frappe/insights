<template>
	<div
		class="flex min-h-[20rem] flex-1 flex-col overflow-scroll rounded-md bg-white p-2 scrollbar-hide lg:w-1/3 lg:pb-2"
	>
		<div v-if="!addingColumn && !editingColumn" class="flex h-full w-full flex-col">
			<div class="pb-3">
				<div class="flex items-center justify-between bg-white">
					<div class="text-sm tracking-wide text-gray-600">COLUMNS</div>
					<Button icon="plus" @click="addingColumn = true"></Button>
				</div>
			</div>
			<div class="h-[calc(100%-3rem)] w-full">
				<ColumnList
					@edit-column="(column) => ([editColumn, editingColumn] = [column, true])"
				></ColumnList>
			</div>
		</div>
		<ColumnPicker v-if="addingColumn" @close="addingColumn = false" />
		<ColumnEditor v-if="editingColumn" @close="editingColumn = false" :column="editColumn" />
	</div>
</template>

<script setup>
import ColumnList from '@/query/Column/ColumnList.vue'
import ColumnPicker from '@/query/Column/ColumnPicker.vue'
import ColumnEditor from '@/query/Column/ColumnEditor.vue'

import { ref } from 'vue'

const addingColumn = ref(false)
const editColumn = ref({})
const editingColumn = ref(false)
</script>
