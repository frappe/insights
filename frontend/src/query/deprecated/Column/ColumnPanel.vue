<template>
	<div class="flex flex-1 flex-shrink-0 flex-col overflow-hidden text-gray-900">
		<template v-if="!addingColumn && !editingColumn">
			<div class="flex w-full flex-shrink-0 items-center justify-between bg-white pb-2">
				<div class="text-sm tracking-wide text-gray-700">COLUMNS</div>
				<Button icon="plus" @click="addingColumn = true"></Button>
			</div>
			<div class="w-full flex-1 overflow-hidden">
				<ColumnList
					@edit-column="(column) => ([editColumn, editingColumn] = [column, true])"
				></ColumnList>
			</div>
		</template>
		<ColumnPicker v-if="addingColumn" @close="addingColumn = false" />
		<ColumnEditor v-if="editingColumn" @close="editingColumn = false" :column="editColumn" />
	</div>
</template>

<script setup>
import ColumnEditor from './ColumnEditor.vue'
import ColumnList from './ColumnList.vue'
import ColumnPicker from './ColumnPicker.vue'

import { ref } from 'vue'

const addingColumn = ref(false)
const editColumn = ref({})
const editingColumn = ref(false)
</script>
