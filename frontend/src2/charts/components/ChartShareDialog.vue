<script setup lang="ts">
import { Globe } from 'lucide-vue-next'
import { __ } from '../../translation'
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
		v-model:open="show"
		:title="__('Share Chart')"
		:actions="[
			{
				label: __('Done'),
				variant: 'solid',
				disabled: !hasChanged,
				onClick: saveChanges,
			},
		]"
	>
		<template #default>
			<div class="space-y-3 text-base">
				<div class="space-y-4">
					<div class="flex items-center gap-3 rounded border px-3 py-2">
						<Globe class="h-6 w-6 text-ink-blue-6" stroke-width="1.5" />
						<div class="flex flex-1 flex-col">
							<div class="font-medium leading-5 text-ink-gray-7">
								Enable Public Access
							</div>
							<div class="text-sm text-ink-gray-6">
								Anyone with the link can view this chart
							</div>
						</div>
						<Toggle v-model="isPublic" />
					</div>
					<div v-if="shareLink" class="flex overflow-hidden rounded bg-surface-gray-2">
						<div
							class="font-code form-input flex-1 overflow-hidden text-ellipsis whitespace-nowrap rounded-r-none text-sm text-ink-gray-5"
						>
							{{ shareLink }}
						</div>
						<Tooltip text="Copy Link" :hoverDelay="0.1">
							<Button
								class="w-8 rounded-none bg-surface-gray-3 hover:bg-surface-gray-4"
								icon="lucide-link-2"
								@click="copyToClipboard(shareLink)"
							>
							</Button>
						</Tooltip>
						<Tooltip text="Copy iFrame" :hoverDelay="0.1">
							<Button
								class="w-8 rounded-l-none bg-surface-gray-3 hover:bg-surface-gray-4"
								icon="lucide-code"
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
