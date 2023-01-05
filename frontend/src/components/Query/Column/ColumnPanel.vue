<template>
	<div class="flex h-full w-1/3 flex-col overflow-scroll px-4 pb-2 scrollbar-hide">
		<div v-if="!addingColumn && !editingColumn" class="flex h-full w-full flex-col">
			<div class="pb-3 pt-1">
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
import ColumnList from '@/components/Query/Column/ColumnList.vue'
import ColumnPicker from '@/components/Query/Column/ColumnPicker.vue'
import ColumnEditor from '@/components/Query/Column/ColumnEditor.vue'

import { ref } from 'vue'

const addingColumn = ref(false)
const editColumn = ref({})
const editingColumn = ref(false)
</script>
