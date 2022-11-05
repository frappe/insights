<template>
	<div class="flex flex-col text-base">
		<span class="mb-2 block text-sm leading-4 text-gray-700"> Attach File </span>
		<input
			ref="fileInput"
			id="attachment"
			type="file"
			accept=".csv"
			class="hidden"
			:disabled="!!value"
			@input="selectFile"
		/>

		<!-- Upload Button -->
		<Button class="h-7 text-sm" v-if="!value" @click="upload">
			<FeatherIcon name="upload" class="mr-1 inline-block h-3 w-3" /> Upload a file
		</Button>

		<!-- Clear Button -->
		<Button class="h-7 text-sm" v-if="value && !isReadOnly" iconRight="x" @click="clear">
			{{ value.name }}
		</Button>
	</div>
</template>
<script>
import { convertFileToDataURL } from '@/utils'
import { defineComponent } from 'vue'

export default defineComponent({
	props: {
		value: Object,
		isReadOnly: Boolean,
		placeholder: String,
		label: String,
	},
	methods: {
		upload() {
			this.$refs.fileInput.click()
		},
		clear() {
			this.$refs.fileInput.value = ''
			this.$emit('change', null)
		},
		async selectFile(e) {
			const target = e.target
			const file = target.files?.[0]
			if (!file) {
				return
			}

			const attachment = await this.getAttachment(file)
			this.$emit('change', attachment)
		},
		async getAttachment(file) {
			if (!file) {
				return null
			}

			const name = file.name
			const type = file.type
			const data = await convertFileToDataURL(file, type)
			return { name, type, data }
		},
	},
})
</script>
