<template>
	<div class="flex flex-col overflow-hidden text-base">
		<span class="mb-2 block text-sm leading-4 text-gray-700">
			{{ label || 'Attach File' }}
		</span>
		<input
			ref="fileInput"
			id="attachment"
			type="file"
			:accept="fileType"
			class="hidden"
			:disabled="!!file"
			@input="selectFile"
		/>

		<!-- Upload Button -->
		<Button v-if="!file?.name" @click="upload" :loading="uploading">
			<FeatherIcon name="upload" class="mr-1 inline-block h-3 w-3" />
			{{ placeholder || 'Upload a file' }}
		</Button>

		<!-- Clear Button -->
		<Button v-else iconRight="x" @click="clear">
			<span class="truncate">{{ file.file_name }}</span>
		</Button>
	</div>
</template>

<script setup>
import FileUploadHandler from 'frappe-ui/src/utils/fileUploadHandler'
import { computed, ref } from 'vue'

const emit = defineEmits(['update:modelValue'])
const props = defineProps({
	modelValue: Object | null,
	placeholder: String,
	label: String,
	fileType: String,
})

const file = computed({
	get: () => props.modelValue,
	set: (val) => emit('update:modelValue', val),
})

const fileInput = ref(null)
function upload() {
	fileInput.value.click()
}
function clear() {
	fileInput.value.value = ''
	file.value = null
}

const uploading = ref(false)
async function selectFile(e) {
	const newFile = e.target.files?.[0]
	if (!newFile) return

	uploading.value = true
	const uploader = new FileUploadHandler()
	uploader
		.upload(newFile, {})
		.then((data) => {
			file.value = data
		})
		.catch((error) => {
			file.value = null
			console.error(error)
		})
		.finally(() => {
			uploading.value = false
		})
}
</script>
