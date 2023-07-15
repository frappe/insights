<script setup>
import { Dialog as HDialog, DialogOverlay, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { computed } from 'vue'
import DashboardQueryEditor from './DashboardQueryEditor.vue'

const emit = defineEmits(['update:show', 'close'])
const props = defineProps({
	show: { type: Boolean, required: true },
	query: { type: String, required: true },
})
const show = computed({
	get: () => props.show,
	set: (value) => {
		emit('update:show', value)
		if (!value) emit('close')
	},
})
function openQueryInNewTab() {
	window.open(`/insights/query/build/${props.query}`, '_blank')
}
</script>

<template>
	<TransitionRoot as="template" :show="show">
		<HDialog as="div" class="fixed inset-0 z-10 overflow-y-auto" @close="show = false">
			<div class="flex h-full min-h-screen flex-col items-center p-10">
				<TransitionChild
					as="template"
					enter="ease-out duration-300"
					enter-from="opacity-0"
					enter-to="opacity-100"
					leave="ease-in duration-200"
					leave-from="opacity-100"
					leave-to="opacity-0"
				>
					<DialogOverlay
						class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"
					/>
				</TransitionChild>

				<TransitionChild
					as="template"
					enter="ease-out duration-300"
					enter-from="opacity-0 translate-y-4 sm:-translate-y-12 sm:scale-95"
					enter-to="opacity-100 translate-y-0 sm:scale-100"
					leave="ease-in duration-200"
					leave-from="opacity-100 translate-y-0 sm:scale-100"
					leave-to="opacity-0 translate-y-4 sm:translate-y-0 sm:scale-95"
				>
					<div
						class="flex h-full w-full max-w-7xl transform gap-2 overflow-hidden text-base transition-all"
					>
						<div v-if="show" class="flex-1 overflow-hidden rounded bg-white shadow-xl">
							<DashboardQueryEditor :name="props.query" class="h-full" />
						</div>
						<div v-if="show" class="flex flex-shrink-0 flex-col space-y-2">
							<Button
								apperance="white"
								icon="x"
								class="shadow-xl"
								@click="show = false"
							></Button>
							<Button
								apperance="white"
								icon="maximize-2"
								class="shadow-xl"
								@click="openQueryInNewTab"
							></Button>
						</div>
					</div>
				</TransitionChild>
			</div>
		</HDialog>
	</TransitionRoot>
</template>
