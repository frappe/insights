<script setup>
import { computed } from 'vue'
import PostgreSQLForm from './PostgreSQLForm.vue'

const props = defineProps({ show: Boolean })
const emit = defineEmits(['update:show'])
const show = computed({
	get: () => props.show,
	set: (value) => emit('update:show', value),
})
</script>
<template>
	<Dialog v-model="show" :options="{ title: 'Connect to PostgreDB' }">
		<template #body-content>
			<PostgreSQLForm @submit="show = false" />
		</template>
	</Dialog>
</template>
