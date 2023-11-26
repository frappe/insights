<template>
	<LoginBox class="bg-gray-50" title="Log in to your account">
		<form class="flex flex-col" @submit.prevent="makeLoginRequest">
			<FormControl
				label="Email"
				placeholder="johndoe@mail.com"
				v-model="email"
				name="email"
				autocomplete="email"
				:type="email !== 'Administrator' ? 'email' : 'text'"
				required
			/>
			<FormControl
				class="mt-4"
				label="Password"
				type="password"
				placeholder="•••••"
				v-model="password"
				name="password"
				autocomplete="current-password"
				required
			/>
			<ErrorMessage :error="errorMessage" class="!mt-2" />
			<Button
				class="mt-4"
				variant="solid"
				:disabled="loggingIn"
				:loading="loggingIn"
				@click="makeLoginRequest"
			>
				Log in with email
			</Button>
		</form>
	</LoginBox>
</template>

<script setup>
import LoginBox from '@/components/LoginBox.vue'
import sessionStore from '@/stores/sessionStore'
import { onMounted, ref } from '@vue/runtime-core'
import { useRoute, useRouter } from 'vue-router'

const session = sessionStore()

const loggingIn = ref(null)
const email = ref(null)
const password = ref(null)
const errorMessage = ref(null)
const redirectRoute = ref(null)

const route = useRoute()
const router = useRouter()
onMounted(() => {
	if (route?.query?.route) {
		redirectRoute.value = route.query.route
		router.replace({ query: null })
	}
})
const makeLoginRequest = async () => {
	if (!email.value || !password.value) {
		return
	}
	try {
		errorMessage.value = null
		loggingIn.value = true
		let res = await session.login(email.value, password.value)
		if (res) {
			router.push(redirectRoute.value || '/')
		}
	} catch (error) {
		console.error(error)
		errorMessage.value = error.messages.join('\n')
	} finally {
		loggingIn.value = false
	}
}
</script>
