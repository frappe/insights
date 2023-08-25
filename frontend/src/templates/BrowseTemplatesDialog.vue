<script setup>
import DialogWithSidebar from '@/components/DialogWithSidebar.vue'
import { Globe, User } from 'lucide-vue-next'
import { computed, ref, markRaw } from 'vue'
import MyTemplates from './MyTemplates.vue'
import TemplatesBrowser from './TemplatesBrowser.vue'

const emit = defineEmits(['update:show'])
const props = defineProps({
	show: Boolean,
	activeTab: String,
})

const show = computed({
	get: () => props.show,
	set: (value) => emit('update:show', value),
})

const tabs = ref([
	{
		label: 'Browse Templates',
		component: markRaw(TemplatesBrowser),
		icon: markRaw(Globe),
	},
	{
		label: 'My Templates',
		component: markRaw(MyTemplates),
		icon: markRaw(User),
	},
])
const activeTab = ref(
	props.activeTab ? tabs.value.find((t) => t.label === props.activeTab) : tabs.value[0]
)
</script>

<template>
	<DialogWithSidebar v-model:show="show" :tabs="tabs" :active-tab="activeTab" />
</template>
