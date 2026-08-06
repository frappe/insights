<script setup lang="ts">
import { watchDebounced } from '@vueuse/core'
import { SearchIcon } from 'lucide-vue-next'
import { computed, ref } from 'vue'
import { __ } from '../translation'
import useUserStore, { User } from '../users/users'

const props = defineProps<{
	placeholder?: string
	hideUsers?: string[]
	// only for pickers whose server side rejects an address that belongs to
	// nobody - otherwise a typo becomes a silent grant
	allowCustomEmail?: boolean
}>()
const selectedUserEmail = defineModel<string>()

const userStore = useUserStore()
const query = ref('')
const matches = ref<User[]>([])

watchDebounced(
	query,
	() => {
		const term = query.value
		userStore.searchUsers(term).then((res) => {
			// a slow answer for an earlier term must not replace a later one
			if (term === query.value) matches.value = res
		})
	},
	{ debounce: 300, immediate: true },
)

const isEmail = (value: string) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value.trim())

const options = computed(() => {
	const hidden = new Set(props.hideUsers || [])
	const found = matches.value
		.filter((user) => user.enabled && !hidden.has(user.email))
		.map((user) => ({
			...user,
			label: user.full_name,
			value: user.email,
			description: user.email,
		}))

	const address = query.value.trim()
	if (!props.allowCustomEmail || found.length || !isEmail(address) || hidden.has(address)) {
		return found
	}

	// nobody to browse here, so let the address stand on its own - the server
	// decides whether it belongs to an Insights user
	return [{ label: address, value: address, description: __('Share with this address') }]
})

const emptyText = computed(() =>
	props.allowCustomEmail
		? __('No matches. Type a full email address to share.')
		: __('No matches.'),
)
</script>

<template>
	<Combobox
		class="w-full"
		v-model:query="query"
		:filterable="false"
		:loading="userStore.searching"
		:modelValue="selectedUserEmail"
		@update:modelValue="selectedUserEmail = $event"
		:options="options"
		:placeholder="props.placeholder || __('Search user...')"
		:emptyText="emptyText"
	>
		<template #prefix>
			<SearchIcon class="h-4 w-4 text-ink-gray-4" stroke-width="1.5" />
		</template>

		<template #item-prefix="{ item }">
			<Avatar size="sm" :label="item.label" :image="item.user_image" />
		</template>
	</Combobox>
</template>
