<script setup>
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
		<Button
			v-if="!editing"
			icon="edit"
			appearance="minimal"
			@click="
				() => {
					editing = true
					oldTitle = title
					$nextTick(() => $refs.titleInput.$el.focus())
				}
			"
		></Button>
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
