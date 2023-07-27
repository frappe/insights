<script setup>
import { computed } from 'vue'
import FileSourceForm from './FileSourceForm.vue'

const emit = defineEmits(['update:show'])
const props = defineProps({ show: Boolean })
const show = computed({
	get: () => props.show,
	set: (val) => emit('update:show', val),
})
</script>

<template>
	<Dialog :options="{ title: 'CSV Import' }" v-model="show">
		<template #body-content>
			<FileSourceForm @submit="show = false" />
		</template>
	</Dialog>
</template>
