import dayjs from 'dayjs'
import relativeTime from 'dayjs/esm/plugin/relativeTime'
import quarterOfYear from 'dayjs/esm/plugin/quarterOfYear'
import advancedFormat from 'dayjs/esm/plugin/advancedFormat'
import customParseFormat from 'dayjs/esm/plugin/customParseFormat'

dayjs.extend(relativeTime)
dayjs.extend(quarterOfYear)
dayjs.extend(advancedFormat)
dayjs.extend(customParseFormat)

export default dayjs
