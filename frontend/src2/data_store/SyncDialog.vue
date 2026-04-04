<script setup lang="ts">
import { ref, watch } from 'vue'
import useDataStore, { DataStoreTable } from './data_store'
import { __ } from '../translation'

const show = defineModel<boolean>({ default: false })
const props = defineProps<{ table: DataStoreTable | null }>()

const dataStore = useDataStore()
const isLoading = ref(false)
const selectedMode = ref('Incremental Sync')

watch(show, (val) => {
	if (val) {
		selectedMode.value = 'Incremental Sync'
		isLoading.value = false
	}
})

async function sync() {
	if (!props.table) return
	isLoading.value = true
	try {
		if (selectedMode.value === 'Incremental Sync') {
			await dataStore.syncTable(props.table.data_source, props.table.table_name)
		} else {
			await dataStore.fullRefreshTable(props.table.data_source, props.table.table_name)
		}
		show.value = false
		dataStore.getTables()
	} finally {
		isLoading.value = false
	}
}
</script>

<template>
	<Dialog :modelValue="show" @update:modelValue="show = $event" :options="{ title: __('Sync Table'), size: 'sm' }">
		<template #body-content>
			<div class="flex flex-col gap-3">
				<p class="text-sm text-gray-600">
					{{ __('Choose how to sync') }}
					<span class="font-medium text-gray-800">{{ props.table?.table_name }}</span>
				</p>

				<div
					class="flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors"
					:class="selectedMode === 'Incremental Sync' ? 'border-blue-500 bg-blue-50' : 'hover:bg-gray-50'"
					@click="selectedMode = 'Incremental Sync'"
				>
					<div class="flex-1">
						<p class="text-sm font-medium text-gray-900">{{ __('Incremental Sync') }}</p>
						<p class="mt-0.5 text-xs text-gray-500">
							{{ __('Only syncs new and modified rows. Faster and recommended for most cases.') }}
						</p>
					</div>
					<span class="flex-shrink-0 text-xs text-green-600">{{ __('Recommended') }}</span>
				</div>

				<div
					class="flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors"
					:class="selectedMode === 'Full Refresh' ? 'border-blue-500 bg-blue-50' : 'hover:bg-gray-50'"
					@click="selectedMode = 'Full Refresh'"
				>
					<div class="flex-1">
						<p class="text-sm font-medium text-gray-900">{{ __('Full Refresh') }}</p>
						<p class="mt-0.5 text-xs text-gray-500">
							{{ __('Replaces all data with a fresh copy from the source. Slower but ensures complete accuracy.') }}
						</p>
					</div>
				</div>

				<div class="flex justify-end gap-2 pt-1">
					<Button :label="__('Cancel')" variant="outline" @click="show = false" />
					<Button
						:label="__('Sync Now')"
						variant="solid"
						:loading="isLoading"
						@click="sync"
					/>
				</div>
			</div>
		</template>
	</Dialog>
</template>
