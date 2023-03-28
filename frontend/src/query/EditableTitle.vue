<script setup>
import { Edit } from 'lucide-vue-next'
import { ref } from 'vue'

defineEmits(['update'])
const props = defineProps({
	title: {
		type: String,
		required: true,
	},
})

const oldTitle = ref(props.title)
const title = ref(props.title)
const editing = ref(false)
</script>

<template>
	<div v-if="!editing" class="flex h-full items-center overflow-hidden">
		<div class="mr-2 whitespace-nowrap text-xl">
			{{ title }}
		</div>
		<div
			v-if="!editing"
			class="flex cursor-pointer items-center rounded-md p-2 transition-all hover:bg-gray-200"
			@click="
				() => {
					editing = true
					oldTitle = title
					$nextTick(() => $refs.titleInput.$el.focus())
				}
			"
		>
			<Edit class="h-3.5 w-3.5" stroke-width="1.5" />
		</div>
	</div>
	<div v-else class="flex space-x-2">
		<Input
			ref="titleInput"
			type="text"
			:value="title"
			@input="(val) => (title = val)"
			:size="title.length + 1"
			class="h-8 text-xl"
		/>
		<Button
			v-if="editing"
			icon="x"
			@click="
				() => {
					editing = false
					title = oldTitle
				}
			"
		></Button>
		<Button
			v-if="editing"
			icon="check"
			appearance="primary"
			@click="
				() => {
					$emit('update', title)
					editing = false
				}
			"
		></Button>
	</div>
</template>
