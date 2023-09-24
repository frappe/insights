<template>
	<Dialog v-model="show" :dismissable="true">
		<template #body>
			<div class="bg-white px-4 py-5 sm:p-6">
				<h3 class="mb-3 text-lg font-medium leading-6 text-gray-900">
					{{ title }}
				</h3>
				<div class="space-y-3 text-base">
					<div v-if="props.allowPublicAccess" class="space-y-4">
						<div class="flex items-center space-x-4 rounded border px-4 py-2">
							<FeatherIcon name="globe" class="h-5 w-5 text-blue-500" />
							<div class="flex flex-1 flex-col">
								<div class="font-medium text-gray-600">Create Public Link</div>
								<div class="text-sm text-gray-500">
									Anyone with the link can view this
									{{ resourceType.replace('Insights ', '').toLowerCase() }}
								</div>
							</div>
							<Checkbox v-model="isPublic" />
						</div>
						<div class="flex overflow-hidden rounded bg-gray-100" v-if="publicLink">
							<div
								class="font-code form-input flex-1 overflow-hidden text-ellipsis whitespace-nowrap rounded-r-none text-sm text-gray-600"
							>
								{{ publicLink }}
							</div>
							<Tooltip text="Copy Link" :hoverDelay="0.1">
								<Button
									class="w-8 rounded-none bg-gray-200 hover:bg-gray-300"
									icon="link-2"
									@click="copyToClipboard(publicLink)"
								>
								</Button>
							</Tooltip>
							<Tooltip text="Copy iFrame" :hoverDelay="0.1">
								<Button
									class="w-8 rounded-l-none bg-gray-200 hover:bg-gray-300"
									icon="code"
									@click="copyToClipboard(iFrame)"
								>
								</Button>
							</Tooltip>
						</div>
					</div>

					<div v-if="settings.enable_permissions">
						<Autocomplete
							v-model="newTeam"
							placeholder="Add a team to share with"
							:options="unauthorizedTeams"
							:autofocus="false"
							@update:modelValue="handleAccessGrant"
						/>
						<div class="space-y-3">
							<div class="font-medium text-gray-600">Teams with access</div>
							<div v-if="authorizedTeams.length > 0" class="space-y-3">
								<div
									class="flex items-center text-gray-600"
									v-for="team in authorizedTeams"
									:key="team.name"
								>
									<Avatar :label="team.team_name" />
									<div class="ml-2 flex flex-col">
										<span>{{ team.team_name }}</span>
										<span class="text-gray-500"
											>{{ team.members_count }} members</span
										>
									</div>
									<Button
										icon="x"
										class="ml-auto"
										variant="minimal"
										@click="handleAccessRevoke(team.name)"
									></Button>
								</div>
							</div>

							<div
								v-else
								class="flex h-20 items-center justify-center rounded border-2 border-dashed text-sm font-light text-gray-500"
							>
								Only you have access to this
								{{ resourceType.replace('Insights ', '').toLowerCase() }}
							</div>
						</div>
					</div>
				</div>
			</div>
		</template>
	</Dialog>
</template>

<script setup>
import settingsStore from '@/stores/settingsStore'
import { copyToClipboard } from '@/utils'
import { createResource } from 'frappe-ui'
import { computed, ref, watch } from 'vue'

const settings = settingsStore().settings
const emit = defineEmits(['update:show', 'togglePublicAccess'])
const props = defineProps({
	show: {
		type: Boolean,
		required: true,
	},
	resourceType: {
		type: String,
		required: true,
	},
	resourceName: {
		type: String,
		required: true,
	},
	allowPublicAccess: {
		type: Boolean,
		default: false,
	},
	isPublic: {
		type: Boolean,
		default: false,
	},
})

const show = computed({
	get: () => props.show,
	set: (value) => {
		emit('update:show', value)
	},
})

const title = computed(() => {
	return `Share ${props.resourceType.replace('Insights ', '')}`
})

const isPublic = computed({
	get: () => props.isPublic,
	set: (value) => {
		emit('togglePublicAccess', value ? 1 : 0)
	},
})
const getPublicKey = createResource({
	url: 'insights.api.public.get_public_key',
	params: {
		resource_type: props.resourceType,
		resource_name: props.resourceName,
	},
})
watch(
	isPublic,
	(newVal, oldVal) => {
		if (newVal && !oldVal) {
			getPublicKey.fetch()
		}
	},
	{ immediate: true }
)
const publicLink = computed(() => {
	const publickKey = getPublicKey.data
	const base = `${window.location.origin}/insights/public/dashboard/`
	return isPublic.value && publickKey ? base + publickKey : null
})
const iFrame = computed(() => {
	const publickKey = getPublicKey.data
	const base = `${window.location.origin}/insights/public/dashboard/`
	const iframeAttrs = `width="800" height="600" frameborder="0" allowtransparency`
	return isPublic.value && publickKey
		? `<iframe src="${base + publickKey}" ${iframeAttrs}></iframe>`
		: null
})

const getAccessInfo = createResource({
	url: 'insights.api.permissions.get_resource_access_info',
	params: {
		resource_type: props.resourceType,
		resource_name: props.resourceName,
	},
})
watch(show, (newVal, oldVal) => {
	if (newVal && !oldVal) {
		getAccessInfo.fetch()
	}
})

const authorizedTeams = computed(() => {
	return getAccessInfo.data?.authorized_teams || []
})

const newTeam = ref(null)
const unauthorizedTeams = computed(() => {
	return getAccessInfo.data?.unauthorized_teams.map((team) => {
		return {
			label: team.team_name,
			value: team.name,
			description: team.members_count + ' members',
		}
	})
})

const grantAccess = createResource({
	url: 'insights.api.permissions.grant_access',
})
function handleAccessGrant(team) {
	grantAccess
		.submit({
			resource_type: props.resourceType,
			resource_name: props.resourceName,
			team: team.value,
		})
		.then(() => {
			getAccessInfo.fetch()
		})
	newTeam.value = null
}

const revokeAccess = createResource({
	url: 'insights.api.permissions.revoke_access',
})
function handleAccessRevoke(team) {
	revokeAccess
		.submit({
			resource_type: props.resourceType,
			resource_name: props.resourceName,
			team: team,
		})
		.then(() => {
			getAccessInfo.fetch()
		})
}
</script>
