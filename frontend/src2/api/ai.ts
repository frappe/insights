import { call } from 'frappe-ui'
import type { Operation } from '../types/query.types'

export type GenerateAIQueryResponse = {
	session_id: string
	question: string
	operations: Operation[]
	attempts: number
	error?: string
}

export type FollowUpResponse = GenerateAIQueryResponse & {
	is_modification: boolean
}

export type SessionInfo = {
	session_id: string
	data_source: string
	question: string
	operations: Operation[]
	messages: Array<{
		role: string
		content: string
		operations?: Operation[]
		error?: string
	}>
}

export function createAISession(question: string, data_source: string) {
	return call<GenerateAIQueryResponse>('insights.api.ai_query.create_ai_session', {
		question,
		data_source,
	})
}

export function askFollowUp(session_id: string, question: string) {
	return call<FollowUpResponse>('insights.api.ai_query.ask_follow_up', {
		session_id,
		question,
	})
}

export function getAISession(session_id: string) {
	return call<SessionInfo>('insights.api.ai_query.get_ai_session', {
		session_id,
	})
}

export function listAISessions() {
	return call<Array<{ session_id: string; data_source: string; question: string; message_count: number }>>(
		'insights.api.ai_query.list_ai_sessions'
	)
}

export function deleteAISession(session_id: string) {
	return call('insights.api.ai_query.delete_ai_session', {
		session_id,
	})
}
