<template>
	<LoginBox title="Log in to your account">
		<form class="flex flex-col" @submit.prevent="makeLoginRequest">
			<Input
				label="Email"
				placeholder="johndoe@mail.com"
				v-model="email"
				:type="email !== 'Administrator' ? 'email' : 'text'"
			/>
			<Input
				class="mt-4"
				label="Password"
				type="password"
				placeholder="•••••"
				v-model="password"
			/>
			<ErrorMessage :error="errorMessage" class="mt-4" />
			<Button
				class="mt-4"
				appearance="primary"
				:disabled="loggingIn"
				:loading="loggingIn"
				@click="makeLoginRequest"
			>
				Submit
			</Button>
		</form>
	</LoginBox>
</template>

<script setup>
import LoginBox from '@/components/LoginBox.vue'
import { onMounted, ref } from '@vue/runtime-core'
import { useRoute, useRouter } from 'vue-router'
import { login } from '@/utils/auth'

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
		let res = await login(email.value, password.value)
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
