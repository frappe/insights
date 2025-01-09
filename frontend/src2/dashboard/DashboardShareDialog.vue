<script setup lang="ts">
import { Globe, Lock } from 'lucide-vue-next'
import { computed, inject, ref, unref, watch } from 'vue'
import { Dashboard } from './dashboard'
import { copyToClipboard } from '../helpers'

const show = defineModel()

const dashboard = inject('dashboard') as Dashboard

const isPublic = ref(unref(dashboard.doc.is_public))
const isPrivate = ref(unref(dashboard.doc.secure_embed))

watch(isPublic, (newVal) => {
	if (newVal) isPrivate.value = false;
});
watch(isPrivate, (newVal) => {
	if (newVal) isPublic.value = false;
});
const shareLink = computed(() => dashboard.getShareLink())
const iFrameLink = computed(() => {
	return `<iframe src="${shareLink.value}" width="100%" height="100%" frameborder="0"></iframe>`
})
const secureLink = computed(() => dashboard.getSecureLink())
const hasChanged = computed(() => {
	const prev_public = Boolean(dashboard.doc.is_public)
	const next_public = Boolean(isPublic.value)
	const prev_private = Boolean(dashboard.doc.secure_embed)
	const next_private = Boolean(isPrivate.value)
	return prev_public !== next_public || prev_private !== next_private
})

function saveChanges() {
	if (isPublic.value && isPrivate.value && isPublic.value == isPrivate.value) {
		alert('Public Sharing and Secure Embedding both are not possible at the same time');
	}
	else {
		dashboard.doc.is_public = isPublic.value
		dashboard.doc.secure_embed = isPrivate.value
		dashboard.doc.share_link = shareLink.value
		dashboard.doc.secure_link = secureLink.value
		show.value = false
	}

}
</script>

<template>
	<Dialog v-model="show" :options="{
		title: 'Share Dashboard',
		actions: [
			{
				label: 'Done',
				variant: 'solid',
				disabled: !hasChanged,
				onClick: saveChanges,
			},
		],
	}">
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
								Anyone with the link can view this dashboard
							</div>
						</div>
						<Checkbox v-model="isPublic" />
					</div>
					<div class="flex items-center gap-3 rounded border px-3 py-2">
						<Lock class="h-6 w-6 text-red-500" stroke-width="1.5" />
						<div class="flex flex-1 flex-col">
							<div class="font-medium leading-5 text-gray-800">
								Enable Private Access
							</div>
							<div class="text-sm text-gray-700">
								Only users with auto-generated tokens can view this dashboard
							</div>
						</div>
						<Checkbox v-model="isPrivate" />
					</div>
					<div v-if="shareLink && isPublic" class="flex overflow-hidden rounded bg-gray-100">
						<div
							class="font-code form-input flex-1 overflow-hidden text-ellipsis whitespace-nowrap rounded-r-none text-sm text-gray-600">
							{{ shareLink }}
						</div>
						<Tooltip text="Copy Link" :hoverDelay="0.1">
							<Button class="w-8 rounded-none bg-gray-200 hover:bg-gray-300" icon="link-2"
								@click="copyToClipboard(shareLink)">
							</Button>
						</Tooltip>
						<Tooltip text="Copy iFrame" :hoverDelay="0.1">
							<Button class="w-8 rounded-l-none bg-gray-200 hover:bg-gray-300" icon="code"
								@click="copyToClipboard(iFrameLink)">
							</Button>
						</Tooltip>
					</div>
					<div v-if="secureLink && isPrivate" class="flex flex-col space-y-3 rounded bg-gray-100 p-4">
						<div class="text-gray-700 text-base font-medium">
							<div class="mb-2">
								Private Access Link: Use the following snippet to create a payload to call
								"generate_embed_link" API and get the sharable link.
							</div>
							<div class="mb-2">
								<br>payload = {
          						<br>"resource" : "{{ secureLink }}",
          						<br>"params": { "column_name": 'value' },
          						<br>"user" : "session_user",
          						<br>"exp": round(time.time()) + (60 * (int(10))) // Token valid for 10 Mins
      							<br>}
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>
