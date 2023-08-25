<template>
	<Dialog v-model="show" :options="{ size: '5xl' }">
		<template #body>
			<div class="flex" :style="{ height: 'calc(100vh - 8rem)' }">
				<div class="flex w-52 shrink-0 flex-col bg-gray-50 p-2">
					<h1 v-if="props.title" class="px-2 pt-2 text-lg font-semibold">
						{{ props.title }}
					</h1>
					<div class="mt-3">
						<button
							class="flex h-7 w-full items-center gap-2 rounded px-2 py-1 focus:outline-none"
							:class="[
								activeTab?.label == tab.label
									? 'bg-white shadow-sm'
									: 'hover:bg-gray-100',
							]"
							v-for="tab in props.tabs"
							:key="tab.label"
							@click="activeTab = tab"
						>
							<component
								v-if="tab.icon"
								:is="tab.icon"
								class="h-4 w-4 text-gray-700"
							/>
							<span class="text-base text-gray-800">
								{{ tab.label }}
							</span>
						</button>
					</div>
				</div>
				<div class="flex flex-1 flex-col px-16 pt-10">
					<component v-if="activeTab" :is="activeTab.component" />
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import { computed, ref } from 'vue'

const props = defineProps({
	show: Boolean,
	title: String,
	tabs: Array,
	activeTab: Object,
})

const emit = defineEmits(['update:show'])
const activeTab = ref(props.activeTab || props.tabs[0])
const show = computed({
	get: () => props.show,
	set: (value) => emit('update:show', value),
})
</script>
