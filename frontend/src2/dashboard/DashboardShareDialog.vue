<script setup lang="ts">
import { Globe } from 'lucide-vue-next'
import { computed, inject, ref, unref } from 'vue'
import { Dashboard } from './dashboard'
import { copyToClipboard } from '../helpers'
import UserSelector from '../components/UserSelector.vue'
import useUserStore from '../users/users'

const show = defineModel()

const dashboard = inject('dashboard') as Dashboard

const isPublic = ref(unref(dashboard.doc.is_public))
const shareLink = computed(() => dashboard.getShareLink())
const iFrameLink = computed(() => {
	return `<iframe src="${shareLink.value}" width="100%" height="100%" frameborder="0"></iframe>`
})

const hasChanged = computed(() => {
	const prev = Boolean(dashboard.doc.is_public)
	const next = Boolean(isPublic.value)
	return prev !== next
})

function saveChanges() {
	dashboard.doc.is_public = isPublic.value
	dashboard.doc.share_link = shareLink.value
	dashboard.updateSharedWith(sharedWith.value.map((u) => u.email))
	show.value = false
}

const selectedUserEmail = ref<string>('')
const sharedWith = ref<
	{
		email: string
		full_name: string
		user_image: string
	}[]
>([])
dashboard.getSharedWith().then((users) => {
	sharedWith.value = users
})

const userStore = useUserStore()
function addSharedUser() {
	if (!selectedUserEmail.value) return
	sharedWith.value.push({
		email: selectedUserEmail.value,
		full_name: userStore.getName(selectedUserEmail.value),
		user_image: userStore.getImage(selectedUserEmail.value),
	})
	selectedUserEmail.value = ''
}
</script>

<template>
	<Dialog
		v-model="show"
		:options="{
			title: 'Share Dashboard',
			actions: [
				{
					label: 'Done',
					variant: 'solid',
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
								Anyone with the link can view this dashboard
							</div>
						</div>
						<Toggle v-model="isPublic" />
					</div>

					<hr class="my-2 border-t border-gray-200" />
					<div class="flex flex-col gap-1">
						<span class="text-sm text-gray-600">Users with Access</span>
						<div class="flex w-full gap-2">
							<div class="flex-1">
								<UserSelector
									v-model="selectedUserEmail"
									placeholder="Search by name or email"
									:hide-users="sharedWith.map((u) => u.email)"
								/>
							</div>
							<Button
								class="flex-shrink-0"
								variant="solid"
								label="Share"
								:disabled="!selectedUserEmail"
								@click="addSharedUser"
							></Button>
						</div>
						<div class="mt-2 flex flex-col gap-1 overflow-y-auto">
							<div
								v-for="user in sharedWith"
								:key="user.email"
								class="flex w-full items-center gap-2 py-1"
							>
								<Avatar
									size="xl"
									:label="user.full_name"
									:image="user.user_image"
								/>
								<div class="flex flex-1 flex-col">
									<div class="leading-5">{{ user.full_name }}</div>
									<div class="text-xs text-gray-600">{{ user.email }}</div>
								</div>
								<Button
									variant="ghost"
									icon="x"
									@click="sharedWith.splice(sharedWith.indexOf(user), 1)"
								></Button>
							</div>

							<div
								v-if="sharedWith.length === 0"
								class="rounded border border-dashed border-gray-300 px-32 py-6 text-center text-sm text-gray-500"
							>
								{{
									isPublic
										? 'Anyone with the link can view this dashboard'
										: 'Only you have access to this dashboard'
								}}
							</div>
						</div>
					</div>

					<hr class="my-2 border-t border-gray-200" />
					<div class="flex flex-col gap-1">
						<span class="text-sm text-gray-600">Share Link</span>
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
			</div>
		</template>
	</Dialog>
</template>
