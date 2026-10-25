import { existsSync, readFileSync } from 'node:fs'
import path from 'node:path'

// A standalone checkout must also build without a neighbouring Bench directory.
const configPath = process.env.FRAPPE_BENCH_PATH
    ? path.join(process.env.FRAPPE_BENCH_PATH, 'sites/common_site_config.json')
    : new URL('../../../sites/common_site_config.json', import.meta.url)
const config = existsSync(configPath) ? JSON.parse(readFileSync(configPath, 'utf8')) : {}
const port = Number(process.env.FRAPPE_WEBSERVER_PORT || config.webserver_port || 8000)
if (!Number.isInteger(port) || port < 1 || port > 65535) throw new Error('Invalid Frappe webserver port')

export default {
    '^/(app|api|assets|files|private)': {
        target: `http://127.0.0.1:${port}`,
        ws: true,
        ...(process.env.FRAPPE_SITE_NAME ? { headers: { host: process.env.FRAPPE_SITE_NAME } } : {}),
    },
}
