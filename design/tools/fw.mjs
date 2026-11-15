// Minimal MCP stdio client for figwright: lets us push big SVG files to Figma without
// routing the markup through the chat. Usage:
//   node fw.mjs <jobs.json>
// jobs.json: [{ "tool": "import_svg", "params": {...}, "svgFile": "path.svg" }, ...]
// svgFile (optional) is read and placed into params.svg.
import { spawn } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';

// Путь к установленному @figwright/mcp: переменная FIGWRIGHT_MCP или путь из npx-кэша Дениса.
const FW = process.env.FIGWRIGHT_MCP || 'C:/Users/murue/AppData/Local/npm-cache/_npx/46c8a3977f900313/node_modules/@figwright/mcp/dist/index.mjs';
const jobsPath = resolve(process.argv[2]);
const jobs = JSON.parse(readFileSync(jobsPath, 'utf8'));
const base = dirname(jobsPath);

const child = spawn(process.execPath, [FW], { stdio: ['pipe', 'pipe', 'pipe'] });
child.stderr.on('data', () => {});
let buf = '';
const pending = new Map();
child.stdout.on('data', (d) => {
  buf += d.toString('utf8');
  let i;
  while ((i = buf.indexOf('\n')) >= 0) {
    const line = buf.slice(0, i).trim();
    buf = buf.slice(i + 1);
    if (!line) continue;
    let msg;
    try { msg = JSON.parse(line); } catch { continue; }
    if (msg.id !== undefined && pending.has(msg.id)) {
      pending.get(msg.id)(msg);
      pending.delete(msg.id);
    }
  }
});
let nextId = 1;
const rpc = (method, params) => new Promise((res) => {
  const id = nextId++;
  pending.set(id, res);
  child.stdin.write(JSON.stringify({ jsonrpc: '2.0', id, method, params }) + '\n');
});
const notify = (method, params) => child.stdin.write(JSON.stringify({ jsonrpc: '2.0', method, params }) + '\n');

const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

await rpc('initialize', { protocolVersion: '2025-06-18', capabilities: {}, clientInfo: { name: 'fw-cli', version: '0.1' } });
notify('notifications/initialized', {});

// wait until the plugin is reachable through the leader
for (let t = 0; t < 30; t++) {
  const r = await rpc('tools/call', { name: 'list_files', arguments: {} });
  const txt = r.result?.content?.[0]?.text ?? '';
  if (txt.includes('"sessionId"')) break;
  await sleep(500);
}
await rpc('tools/call', { name: 'use_file', arguments: { fileName: 'ПАК' } });

const call = async (name, args) => {
  const r = await rpc('tools/call', { name, arguments: args });
  return r.result?.content?.map((c) => c.text).join('') ?? JSON.stringify(r.error);
};

const out = [];
for (const job of jobs) {
  // { "screen": { "frame": "5:3043", "svgFile": "a1.svg", "name": "A1 Датасеты" } }
  // clears the frame, imports the SVG at 0,0 and fits the frame to the SVG size.
  if (job.screen) {
    const { frame, svgFile, name } = job.screen;
    const svg = readFileSync(resolve(base, svgFile), 'utf8');
    const w = Number(/<svg[^>]*\swidth="([\d.]+)"/.exec(svg)?.[1] ?? 1440);
    const h = Number(/<svg[^>]*\sheight="([\d.]+)"/.exec(svg)?.[1] ?? 900);
    const info = JSON.parse(await call('get_nodes_info', { nodeIds: [frame] }));
    const kids = (info.nodes?.[0]?.children ?? []).map((c) => (typeof c === 'string' ? c : c.id));
    if (kids.length) await call('delete_nodes', { nodeIds: kids });
    await call('resize_nodes', { nodeIds: [frame], width: w, height: h });
    const res = await call('import_svg', { svg, parentId: frame, x: 0, y: 0, name: (name ?? 'screen') + ' / svg' });
    out.push({ screen: frame, removed: kids.length, size: `${w}x${h}`, result: res.slice(0, 200) });
    continue;
  }
  const params = { ...(job.params || {}) };
  if (job.svgFile) params.svg = readFileSync(resolve(base, job.svgFile), 'utf8');
  const r = await rpc('tools/call', { name: job.tool, arguments: params });
  const txt = r.result?.content?.map((c) => c.text).join('') ?? JSON.stringify(r.error);
  out.push({ tool: job.tool, name: params.name, result: txt.slice(0, 300) });
}
console.log(JSON.stringify(out, null, 1));
child.kill();
process.exit(0);
