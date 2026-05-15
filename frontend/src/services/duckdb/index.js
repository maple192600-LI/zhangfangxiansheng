import * as duckdb from '@duckdb/duckdb-wasm'
import duckdbWasmMvp from '@duckdb/duckdb-wasm/dist/duckdb-mvp.wasm?url'
import mvpWorker from '@duckdb/duckdb-wasm/dist/duckdb-browser-mvp.worker.js?url'
import duckdbWasmEh from '@duckdb/duckdb-wasm/dist/duckdb-eh.wasm?url'
import ehWorker from '@duckdb/duckdb-wasm/dist/duckdb-browser-eh.worker.js?url'

const MANUAL_BUNDLES = {
  mvp: {
    mainModule: duckdbWasmMvp,
    mainWorker: mvpWorker,
  },
  eh: {
    mainModule: duckdbWasmEh,
    mainWorker: ehWorker,
  },
}

const READONLY_PREFIXES = ['select', 'with', 'describe', 'summarize']

let db = null
let worker = null
let status = 'idle'

export function getDuckDBStatus() {
  return status
}

export async function initDuckDB() {
  if (status === 'ready' && db) return
  if (status === 'initializing') {
    throw new Error('DuckDB 正在初始化中，请稍候')
  }

  status = 'initializing'

  try {
    const bundle = await duckdb.selectBundle(MANUAL_BUNDLES)
    worker = new Worker(bundle.mainWorker)
    const logger = new duckdb.ConsoleLogger()
    db = new duckdb.AsyncDuckDB(logger, worker)
    await db.instantiate(bundle.mainModule, bundle.pthreadWorker)
    await db.open({
      query: { castBigIntToDouble: true },
    })
    status = 'ready'
  } catch (e) {
    status = 'idle'
    if (worker) {
      worker.terminate()
      worker = null
    }
    db = null
    throw new Error('DuckDB 初始化失败：' + (e.message || e))
  }
}

export async function replaceJsonRows(tableName, rows) {
  ensureReady()
  const conn = await db.connect()
  try {
    await conn.query(`DROP TABLE IF EXISTS "${tableName}"`)
    const json = JSON.stringify(rows)
    await db.registerFileText(`${tableName}.json`, json)
    await conn.insertJSONFromPath(`${tableName}.json`, { name: tableName })
  } finally {
    await conn.close()
  }
}

export async function queryReadonly(sql) {
  ensureReady()

  const normalized = sql.trim().toLowerCase()
  const allowed = READONLY_PREFIXES.some((p) => normalized.startsWith(p))
  if (!allowed) {
    throw new Error('只允许 SELECT / WITH / DESCRIBE / SUMMARIZE 查询')
  }

  const conn = await db.connect()
  try {
    const result = await conn.query(sql)
    const rows = result.toArray().map((row) => {
      const obj = {}
      for (const key of Object.keys(row)) {
        const val = row[key]
        if (val instanceof BigInt) {
          obj[key] = Number(val)
        } else if (ArrayBuffer.isView(val)) {
          obj[key] = Array.from(val)
        } else {
          obj[key] = val
        }
      }
      return obj
    })
    const columns = rows.length > 0 ? Object.keys(rows[0]) : []
    return { columns, rows }
  } finally {
    await conn.close()
  }
}

export async function closeDuckDB() {
  if (db) {
    try { await db.terminate() } catch { /* ignore */ }
    db = null
  }
  if (worker) {
    worker.terminate()
    worker = null
  }
  status = 'idle'
}

function ensureReady() {
  if (status !== 'ready' || !db) {
    throw new Error('DuckDB 未就绪，请先初始化')
  }
}
