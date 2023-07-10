<script setup>
import { ref } from 'vue'

defineEmits(['update'])
const props = defineProps({
	title: { type: String, required: true },
	disabled: { type: Boolean, default: true },
})

const oldTitle = ref(props.title)
const title = ref(props.title)
const editing = ref(false)
</script>

<template>
	<div v-if="!editing" class="flex overflow-hidden py-1">
		<div class="mr-2 whitespace-nowrap px-1.5 text-2xl font-medium">
			{{ title }}
		</div>
		<Button
			v-if="!editing && !disabled"
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
	<div v-else-if="editing && !disabled" class="flex space-x-2">
		<Input
			ref="titleInput"
			type="text"
			v-model="title"
			:size="title.length + 1"
			class="h-full text-2xl"
		/>
		<Button
			icon="x"
			appearance="secondary"
			@click="() => ((editing = false), (title = oldTitle))"
		></Button>
		<Button
			icon="check"
			appearance="primary"
			@click="() => ((editing = false), $emit('update', title))"
			class="!rounded-lg bg-gray-900 text-gray-50 hover:bg-gray-800"
		></Button>
	</div>
</template>
