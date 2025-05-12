<script setup lang="ts">
import { Globe } from 'lucide-vue-next'
import { computed, ref, unref } from 'vue'
import { copyToClipboard } from '../../helpers'
import { Chart } from '../chart'

const props = defineProps<{ chart: Chart }>()
const show = defineModel()

const chart = props.chart

const isPublic = ref(unref(chart.doc.is_public))
const shareLink = computed(() => chart.getShareLink())
const iFrameLink = computed(() => {
	return `<iframe src="${shareLink.value}" width="100%" height="300" frameborder="0"></iframe>`
})

const hasChanged = computed(() => {
	const prev = Boolean(chart.doc.is_public)
	const next = Boolean(isPublic.value)
	return prev !== next
})

function saveChanges() {
	chart.doc.is_public = isPublic.value
	show.value = false
}
</script>

<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Share Chart',
			actions: [
				{
					label: 'Done',
					variant: 'solid',
					disabled: !hasChanged,
					onClick: saveChanges,
				},
			],
		}"
	>
		<template #body-content>
			<div class="space-y-3 text-base">
				<div class="space-y-4">
					<div class="flex items-center gap-3 rounded border px-3 py-2">
						<Globe class="h-6 w-6 text-blue-500" stroke-width="1.5" />
						<div class="flex flex-1 flex-col">
							<div class="font-medium leading-5 text-gray-800">
								Enable Public Access
							</div>
							<div class="text-sm text-gray-700">
								Anyone with the link can view this chart
							</div>
						</div>
						<Toggle v-model="isPublic" />
					</div>
					<div v-if="shareLink" class="flex overflow-hidden rounded bg-gray-100">
						<div
							class="font-code form-input flex-1 overflow-hidden text-ellipsis whitespace-nowrap rounded-r-none text-sm text-gray-600"
						>
							{{ shareLink }}
						</div>
						<Tooltip text="Copy Link" :hoverDelay="0.1">
							<Button
								class="w-8 rounded-none bg-gray-200 hover:bg-gray-300"
								icon="link-2"
								@click="copyToClipboard(shareLink)"
							>
							</Button>
						</Tooltip>
						<Tooltip text="Copy iFrame" :hoverDelay="0.1">
							<Button
								class="w-8 rounded-l-none bg-gray-200 hover:bg-gray-300"
								icon="code"
								@click="copyToClipboard(iFrameLink)"
							>
							</Button>
						</Tooltip>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
