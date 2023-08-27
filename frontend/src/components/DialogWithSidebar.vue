<template>
	<Dialog
		:modelValue="show"
		:options="{ size: '5xl' }"
		@update:modelValue="props.dismissable ? $emit('update:show', $event) : null"
	>
		<template #body>
			<div class="relative flex" :style="{ height: 'calc(100vh - 8rem)' }">
				<div class="absolute top-4 right-4">
					<Button variant="ghost" @click="show = false">
						<template #icon>
							<FeatherIcon name="x" class="h-5 w-5 text-gray-600" />
						</template>
					</Button>
				</div>
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
	activeTabIdx: Number,
	dismissable: { type: Boolean, default: true },
})

const emit = defineEmits(['update:show'])
const activeTab = ref(props.tabs[props.activeTabIdx || 0])
const show = computed({
	get: () => props.show,
	set: (value) => emit('update:show', value),
})
</script>
