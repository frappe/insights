<script setup lang="ts">
import { Button, Dialog, FormControl } from 'frappe-ui'
import { ref, watch } from 'vue'
import { __ } from '../translation'

const show = defineModel<boolean>({ default: false })

const props = defineProps<{
	downloading?: boolean
	defaultFilename?: string
}>()

const emit = defineEmits<{
	(e: 'export', format: 'csv' | 'excel', filename: string): void
	(e: 'cancel'): void
}>()

const format = ref<'csv' | 'excel'>('csv')
const filename = ref('data')

watch(
	() => props.defaultFilename,
	(val) => {
		if (val) filename.value = val
	},
	{ immediate: true },
)

function submit() {
	emit('export', format.value, filename.value)
}
</script>

<template>
	<Dialog v-model="show" :options="{ title: __('Export Data'), size: 'sm' }">
		<template #body-content>
			<div class="space-y-4">
				<div>
					<div class="space-y-2">
						<label class="flex cursor-pointer items-center ">
							<FormControl
								class="w-32"
								type="select"
								:label="__('Export Format')"
								:options="[
									{ label: 'CSV', value: 'csv' },
									{ label: 'Excel', value: 'excel' },
								]"
								v-model="format"
							/>
						</label>
					</div>
				</div>

				<div class="flex items-center gap-2">
					<FormControl
						type="text"
						:label="__('Filename')"
						v-model="filename"
						:placeholder="__('Enter filename')"
						class="w-44"
					/>
				</div>
			</div>
		</template>

		<template #actions>
			<div class="flex justify-end gap-2">
				<Button variant="ghost" @click="() => { emit('cancel'); show = false }">{{ __('Cancel') }}</Button>
				<Button variant="solid" @click="submit" :loading="props.downloading">{{ __('Export') }}</Button>
			</div>
		</template>
	</Dialog>

</template>
