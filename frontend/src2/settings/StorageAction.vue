<script setup lang="ts">
import { FormControl } from 'frappe-ui'
import { computed, ref } from 'vue'
import { showErrorToast } from '../helpers'
import { __ } from '../translation'
import type { StoredTable } from './data_store_storage'

const props = defineProps<{
	label: string
	title: string
	table: StoredTable
	message: string
	action: () => Promise<unknown>
}>()

const emit = defineEmits<{ done: [] }>()

const confirming = ref(false)
const running = ref(false)
const typedName = ref('')
const needsTypedName = computed(() => props.table.sync_mode === 'Incremental')

function start() {
	typedName.value = ''
	confirming.value = true
}

function run() {
	running.value = true
	return props
		.action()
		.then(() => {
			confirming.value = false
			emit('done')
		})
		.catch((err) => showErrorToast(err, false))
		.finally(() => (running.value = false))
}
</script>

<template>
	<div class="flex shrink-0 items-center gap-1.5">
		<template v-if="confirming && !needsTypedName">
			<Button :label="__('Cancel')" variant="ghost" @click="confirming = false" />
			<Button :label="label" variant="solid" :loading="running" @click="run" />
		</template>
		<Button v-else :label="label" variant="outline" @click="start" />
	</div>

	<Dialog
		v-if="needsTypedName"
		v-model:open="confirming"
		:title="title"
		theme="red"
		:actions="[
			{
				label,
				theme: 'red',
				variant: 'solid',
				disabled: typedName !== table.table,
				onClick: () => run(),
			},
		]"
	>
		<template #default>
			<div class="flex flex-col gap-4">
				<p class="text-p-base text-ink-gray-6">{{ message }}</p>
				<FormControl
					v-model="typedName"
					:label="__('Type {0} to confirm', table.table)"
					autocomplete="off"
				/>
			</div>
		</template>
	</Dialog>
</template>
