/**
 * What a chart's info mark says. A Number card has no line under its title, so
 * there the description goes behind the mark, above the info.
 */
export function infoMarkText(
	description: string | null | undefined,
	info: string | null | undefined,
	cardsOwnTitle: boolean,
): string {
	return [cardsOwnTitle ? description : undefined, info].filter(Boolean).join('\n\n')
}
