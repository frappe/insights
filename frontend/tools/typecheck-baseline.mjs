#!/usr/bin/env node
// Runs vue-tsc, diffs its errors against typecheck-baseline.txt, and fails only on new ones.
// Line/col shift as code is edited, so errors are keyed on path + TS code + message, not position.

import { spawnSync } from 'node:child_process'
import { readFileSync, writeFileSync, existsSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import path from 'node:path'

const frontendDir = path.dirname(path.dirname(fileURLToPath(import.meta.url)))
const baselinePath = path.join(frontendDir, 'typecheck-baseline.txt')
const update = process.argv.includes('--update')

const ERROR_HEAD = /^(.+?)\((\d+),(\d+)\): error (TS\d+): (.*)$/

function runVueTsc() {
	const result = spawnSync(
		path.join(frontendDir, 'node_modules', '.bin', 'vue-tsc'),
		['--noEmit', '-p', 'tsconfig.json'],
		{ cwd: frontendDir, encoding: 'utf8' },
	)
	const output = `${result.stdout || ''}${result.stderr || ''}`
	return output.split('\n')
}

// Groups an error's own line with any indented continuation lines that follow it.
function parseErrors(lines) {
	const errors = []
	let current = null
	for (const line of lines) {
		const head = line.match(ERROR_HEAD)
		if (head) {
			if (current) errors.push(current)
			const [, file, lineNo, colNo, code, message] = head
			current = {
				file: file.split(path.sep).join('/'),
				line: Number(lineNo),
				col: Number(colNo),
				code,
				message,
			}
		} else if (current && /^\s+\S/.test(line)) {
			current.message += ' ' + line.trim()
		} else if (current) {
			errors.push(current)
			current = null
		}
	}
	if (current) errors.push(current)
	return errors
}

// Dependency errors report paths relative to this checkout's location on disk, so they
// only match a baseline on the machine that generated it. Only frontend's own source is stable.
function isFrontendSource(error) {
	const resolved = path.resolve(frontendDir, error.file)
	const relative = path.relative(frontendDir, resolved)
	return !relative.startsWith('..') && !relative.split(path.sep).includes('node_modules')
}

// path + TS code + message identify an error across edits that move line numbers;
// a count per key lets a second copy of the same error in one file still count as new.
function toKey(error) {
	return `${error.file}: ${error.code}: ${error.message}`
}

function toCounts(errors) {
	return toCountsByKeys(errors.map(toKey))
}

function toCountsByKeys(keys) {
	const counts = new Map()
	for (const key of keys) {
		counts.set(key, (counts.get(key) || 0) + 1)
	}
	return counts
}

function readBaseline() {
	if (!existsSync(baselinePath)) return new Map()
	const lines = readFileSync(baselinePath, 'utf8').split('\n').filter(Boolean)
	return toCountsByKeys(lines)
}

function writeBaseline(errors) {
	const keys = errors.map(toKey).sort((a, b) => a.localeCompare(b))
	writeFileSync(baselinePath, keys.join('\n') + (keys.length ? '\n' : ''))
}

const lines = runVueTsc()
const errors = parseErrors(lines).filter(isFrontendSource)

if (update) {
	writeBaseline(errors)
	console.log(`typecheck baseline updated: ${errors.length} error(s)`)
	process.exit(0)
}

const baseline = readBaseline()
const current = toCounts(errors)

const newKeys = []
for (const [key, count] of current) {
	const baselineCount = baseline.get(key) || 0
	if (count > baselineCount) {
		for (let i = baselineCount; i < count; i++) newKeys.push(key)
	}
}

const goneKeys = []
for (const [key, count] of baseline) {
	const currentCount = current.get(key) || 0
	if (currentCount < count) goneKeys.push(key)
}

if (goneKeys.length) {
	console.log(
		`typecheck: ${goneKeys.length} baseline error(s) no longer reproduce — run "yarn typecheck:baseline --update" to shrink the baseline`,
	)
}

if (newKeys.length) {
	console.error(`typecheck: ${newKeys.length} new error(s) not in the baseline:\n`)
	for (const key of newKeys) console.error(`  ${key}`)
	process.exit(1)
}

console.log(`typecheck: no new errors (${errors.length} baseline error(s))`)
