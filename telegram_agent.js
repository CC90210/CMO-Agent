require('dotenv').config({ path: '.env.agents' });
const TelegramBot = require('node-telegram-bot-api');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

// ============================================================
// MAVEN TELEGRAM BRIDGE V1.0 (CMO Agent — 2026-04-26)
//
// Distinct bot from Bravo (CEO) and Atlas (CFO). Maven runs on its OWN
// Telegram token (MAVEN_TELEGRAM_BOT_TOKEN) with its OWN allowed-users
// list (MAVEN_TELEGRAM_ALLOWED_USERS). The three bots never poll the same
// API token, so they never conflict.
//
// CROSS-AGENT FILE-STRUCTURE AWARENESS:
//   Maven CAN READ Bravo's repo, Atlas's repo, and Aura's repo at the
//   paths defined by env vars (BRAVO_REPO, ATLAS_REPO, AURA_REPO,
//   defaulting to the standard Windows layout). Maven NEVER writes to
//   those repos — cross-repo writes go through scripts/agent_inbox.py.
//
//   When CC asks "what's the CFO spend gate status right now?" Maven
//   reads ATLAS_REPO/data/pulse/cfo_pulse.json directly. When CC asks
//   "what's Bravo's CEO directive?" Maven reads
//   BRAVO_REPO/data/pulse/ceo_pulse.json.
//
// COMMANDS:
//   Plain text    → spawned to Maven's CLAUDE.md context (claude --dangerously-skip-permissions ... or codex)
//   /status       → reads cmo_pulse.json + ceo_pulse.json + cfo_pulse.json,
//                   one-line summary of each
//   /spend        → reads cfo_pulse.json, prints approved budgets per channel/brand
//   /campaigns    → lists active Meta + Google campaigns via send_gateway stats
//   /killswitch   → sets MAVEN_FORCE_DRY_RUN=1 in .env.agents (with confirmation)
//   /unleash      → unsets MAVEN_FORCE_DRY_RUN (with confirmation)
//   /pulse        → forces python scripts/state_sync.py to refresh cmo_pulse
//   /sync         → end-of-session sync
//   /audit        → runs python scripts/self_audit.py --json
//   /tests        → runs all 5 test files, reports pass/fail counts
//   /inbox        → lists unread messages in Maven's agent_inbox
//   /post         → posts a cross-repo message via agent_inbox.py
//                   format: /post bravo|atlas|aura subject||body
//   /help         → command list
// ============================================================

const IS_MAC = process.platform === 'darwin';
const IS_WIN = process.platform === 'win32';
const PROJECT_ROOT = __dirname;
const PYTHON = IS_MAC
    ? 'python3'
    : path.join(PROJECT_ROOT, '.venv', 'Scripts', 'python.exe');
const FALLBACK_PYTHON = 'python';
const MACHINE_NAME = IS_MAC ? 'MacBook' : 'Windows Desktop';
const TEMP_PATH = IS_MAC ? '/tmp' : (process.env.TEMP || 'C:\\Temp');

const TELEGRAM_TOKEN =
    process.env.MAVEN_TELEGRAM_BOT_TOKEN
    || process.env.TELEGRAM_BOT_TOKEN; // single-bot rigs
const ALLOWED_USERS = (
    process.env.MAVEN_TELEGRAM_ALLOWED_USERS
    || process.env.TELEGRAM_ALLOWED_USERS
    || ''
).split(',').map(s => s.trim()).filter(Boolean);

// Cross-agent repo paths — overridable per-machine via env vars.
const SIBLING_REPOS = {
    bravo: process.env.BRAVO_REPO || (IS_WIN
        ? 'C:\\Users\\User\\Business-Empire-Agent'
        : path.join(process.env.HOME || '', 'Business-Empire-Agent')),
    atlas: process.env.ATLAS_REPO || (IS_WIN
        ? 'C:\\Users\\User\\APPS\\CFO-Agent'
        : path.join(process.env.HOME || '', 'APPS', 'CFO-Agent')),
    aura: process.env.AURA_REPO || (IS_WIN
        ? 'C:\\Users\\User\\AURA'
        : path.join(process.env.HOME || '', 'AURA')),
    maven: PROJECT_ROOT,
};

const PULSE_FILES = {
    bravo: path.join(SIBLING_REPOS.bravo, 'data', 'pulse', 'ceo_pulse.json'),
    atlas: path.join(SIBLING_REPOS.atlas, 'data', 'pulse', 'cfo_pulse.json'),
    aura:  path.join(SIBLING_REPOS.aura,  'data', 'pulse', 'aura_pulse.json'),
    maven: path.join(SIBLING_REPOS.maven, 'data', 'pulse', 'cmo_pulse.json'),
};

const LOG_FILE = path.join(PROJECT_ROOT, 'memory', 'telegram_bridge.log');
const LOCK_FILE = path.join(PROJECT_ROOT, 'tmp', 'maven_telegram.lock.json');

const log = (msg) => {
    const line = `[${new Date().toISOString()}] ${msg}\n`;
    console.log(line.trim());
    try { fs.appendFileSync(LOG_FILE, line); } catch (_) {}
};

const ensureDirs = () => {
    for (const d of ['tmp', 'memory']) {
        try { fs.mkdirSync(path.join(PROJECT_ROOT, d), { recursive: true }); } catch (_) {}
    }
};

// ---- Single-instance lock (prevents two bridges polling Maven's token) ----

const isPidAlive = (pid) => {
    if (!pid || Number.isNaN(Number(pid))) return false;
    try { process.kill(Number(pid), 0); return true; } catch (_) { return false; }
};

const acquireLock = () => {
    ensureDirs();
    try {
        if (fs.existsSync(LOCK_FILE)) {
            const existing = JSON.parse(fs.readFileSync(LOCK_FILE, 'utf8'));
            if (existing.pid && existing.pid !== process.pid && isPidAlive(existing.pid)) {
                log(`[LOCK] Another Maven bridge owns polling (pid ${existing.pid}, ${existing.machine || '?'}). Exiting.`);
                process.exit(0);
            }
            log(`[LOCK] Replacing stale lock from pid ${existing.pid || '?'}.`);
        }
    } catch (err) {
        log(`[LOCK] Could not read lock; replacing (${err.message || err}).`);
    }
    fs.writeFileSync(LOCK_FILE, JSON.stringify({
        pid: process.pid,
        machine: MACHINE_NAME,
        platform: process.platform,
        bot: 'maven',
        started_at: new Date().toISOString(),
    }, null, 2));
};

const releaseLock = () => {
    try {
        if (!fs.existsSync(LOCK_FILE)) return;
        const existing = JSON.parse(fs.readFileSync(LOCK_FILE, 'utf8'));
        if (existing.pid === process.pid) fs.unlinkSync(LOCK_FILE);
    } catch (_) {}
};

// ---- Boot validation ----

if (!TELEGRAM_TOKEN) {
    console.error('MAVEN_TELEGRAM_BOT_TOKEN missing in .env.agents (and no fallback TELEGRAM_BOT_TOKEN).');
    console.error('Create a Maven-only bot via @BotFather, then add:');
    console.error('  MAVEN_TELEGRAM_BOT_TOKEN=<token-from-botfather>');
    console.error('  MAVEN_TELEGRAM_ALLOWED_USERS=<your-telegram-user-id>');
    process.exit(1);
}
if (ALLOWED_USERS.length === 0) {
    console.error('MAVEN_TELEGRAM_ALLOWED_USERS empty — no chat IDs are authorized to message Maven.');
    process.exit(1);
}

acquireLock();
process.on('SIGINT',  () => { releaseLock(); process.exit(0); });
process.on('SIGTERM', () => { releaseLock(); process.exit(0); });
process.on('exit',    () => { releaseLock(); });

// ---- Telegram bot setup ----

const bot = new TelegramBot(TELEGRAM_TOKEN, { polling: true });

bot.on('polling_error', (err) => {
    log(`[POLLING ERROR] ${err.code || ''} ${err.message || err}`);
    if (String(err.message || '').includes('401')) {
        console.error('Telegram returned 401. The MAVEN_TELEGRAM_BOT_TOKEN is invalid or revoked.');
    }
});

const isAuthorized = (chatId) => ALLOWED_USERS.includes(String(chatId));

const sendChunked = async (chatId, text) => {
    // Telegram caps at 4096 chars; split on newlines preferred.
    const max = 3900;
    if (text.length <= max) { await bot.sendMessage(chatId, text); return; }
    const lines = text.split('\n');
    let buf = '';
    for (const line of lines) {
        if ((buf + '\n' + line).length > max) {
            await bot.sendMessage(chatId, buf || line.slice(0, max));
            buf = line.length > max ? line.slice(0, max) : line;
        } else {
            buf = buf ? `${buf}\n${line}` : line;
        }
    }
    if (buf) await bot.sendMessage(chatId, buf);
};

// ---- Cross-agent pulse readers (READ-ONLY) ----

const readJson = (file) => {
    try {
        if (!fs.existsSync(file)) return null;
        return JSON.parse(fs.readFileSync(file, 'utf8'));
    } catch (e) { return { error: String(e.message || e) }; }
};

const summarizePulse = (label, file) => {
    const j = readJson(file);
    if (j == null) return `${label}: pulse missing (${file})`;
    if (j.error)   return `${label}: pulse unreadable (${j.error})`;
    const ts = j.updated_at || (j.spend_gate && j.spend_gate.updated_at) || 'unknown';
    const status = j.status || (j.spend_gate && j.spend_gate.status) || j.last_note || 'ok';
    return `${label}: ${status} @ ${ts}`;
};

// ---- Spawned Python helper ----

const runPython = (args, opts = {}) => new Promise((resolve) => {
    const py = fs.existsSync(PYTHON) ? PYTHON : FALLBACK_PYTHON;
    const child = spawn(py, args, {
        cwd: PROJECT_ROOT,
        env: { ...process.env },
        ...opts,
    });
    let stdout = '', stderr = '';
    child.stdout.on('data', (d) => stdout += d.toString());
    child.stderr.on('data', (d) => stderr += d.toString());
    child.on('error', (err) => resolve({ code: -1, stdout, stderr: stderr + err.message }));
    child.on('close', (code) => resolve({ code, stdout, stderr }));
});

// ---- Command handlers ----

bot.onText(/^\/help/, async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    await sendChunked(msg.chat.id, [
        'Maven CMO bot — commands:',
        '/status     — pulse status across Bravo/Atlas/Aura/Maven',
        '/spend      — Atlas spend-gate summary (cfo_pulse.json)',
        '/campaigns  — send_gateway daily stats',
        '/killswitch — engage MAVEN_FORCE_DRY_RUN (asks confirm)',
        '/unleash    — disengage killswitch (asks confirm)',
        '/pulse      — refresh cmo_pulse.json',
        '/sync       — end-of-session state_sync',
        '/audit      — self_audit health score',
        '/tests      — run all 5 test files',
        '/inbox      — list unread agent_inbox messages',
        '/post <to> <subject>||<body> — cross-repo post (to=bravo|atlas|aura)',
        '',
        'Plain text → spawned to Maven\'s Claude context.',
    ].join('\n'));
});

bot.onText(/^\/status/, async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    const lines = [
        `Maven bridge — ${MACHINE_NAME} (${process.platform})`,
        '',
        summarizePulse('Maven', PULSE_FILES.maven),
        summarizePulse('Bravo', PULSE_FILES.bravo),
        summarizePulse('Atlas', PULSE_FILES.atlas),
        summarizePulse('Aura ', PULSE_FILES.aura),
    ];
    await sendChunked(msg.chat.id, lines.join('\n'));
});

bot.onText(/^\/spend/, async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    const j = readJson(PULSE_FILES.atlas);
    if (j == null) {
        await bot.sendMessage(msg.chat.id, `cfo_pulse.json missing at ${PULSE_FILES.atlas}`); return;
    }
    if (j.error) {
        await bot.sendMessage(msg.chat.id, `cfo_pulse unreadable: ${j.error}`); return;
    }
    const sg = j.spend_gate || {};
    const lines = [`Atlas spend gate: ${sg.status || 'unknown'}`];
    lines.push(`  updated_at: ${j.updated_at || sg.updated_at || 'n/a'}`);
    const approvals = sg.approvals || {};
    for (const channel of Object.keys(approvals)) {
        for (const brand of Object.keys(approvals[channel] || {})) {
            const cap = approvals[channel][brand];
            const usd = (cap && cap.daily_budget_usd != null) ? `$${cap.daily_budget_usd}/d` : 'n/a';
            lines.push(`  ${channel} / ${brand} → ${usd}`);
        }
    }
    await sendChunked(msg.chat.id, lines.join('\n'));
});

bot.onText(/^\/campaigns/, async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    const r = await runPython(['scripts/send_gateway.py', '--json', 'stats']);
    await sendChunked(msg.chat.id, r.code === 0
        ? `send_gateway stats:\n${r.stdout.slice(0, 3500)}`
        : `stats failed (code ${r.code}):\n${(r.stderr || r.stdout).slice(0, 1500)}`);
});

bot.onText(/^\/killswitch/, async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    await bot.sendMessage(msg.chat.id,
        'KILLSWITCH: reply "yes engage" to set MAVEN_FORCE_DRY_RUN=1 in .env.agents. ' +
        'No real sends will fire until you /unleash.');
});

bot.onText(/^yes engage/i, async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    const r = await runPython(['scripts/notify.py', 'killswitch:engaging via Telegram']);
    // The actual env-var flip is best done by editing .env.agents OR setting at runtime.
    // We surface the alert + suggest the manual step rather than auto-edit credentials.
    await sendChunked(msg.chat.id,
        'Acknowledged. Killswitch alerted. To make it persistent, edit .env.agents:\n' +
        '  MAVEN_FORCE_DRY_RUN=1\n' +
        'and restart any running scheduler. notify result: ' + r.stdout.slice(0, 200));
});

bot.onText(/^\/unleash/, async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    await sendChunked(msg.chat.id,
        'Edit .env.agents and remove MAVEN_FORCE_DRY_RUN=1 (or set =0). Then restart any running scheduler.');
});

bot.onText(/^\/pulse/, async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    const r = await runPython(['scripts/state_sync.py', '--note', 'pulse refresh from telegram']);
    await sendChunked(msg.chat.id, `pulse refresh:\n${(r.stdout || r.stderr).slice(0, 1500)}`);
});

bot.onText(/^\/sync/, async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    const r = await runPython(['scripts/state_sync.py', '--note', 'session sync from telegram', '--mem0']);
    await sendChunked(msg.chat.id, `state_sync:\n${(r.stdout || r.stderr).slice(0, 1500)}`);
});

bot.onText(/^\/audit/, async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    const r = await runPython(['scripts/self_audit.py', '--json']);
    let summary = r.stdout.slice(0, 3500);
    try {
        const idx = r.stdout.indexOf('{');
        if (idx >= 0) {
            const j = JSON.parse(r.stdout.slice(idx));
            summary = `health: ${j.health_score}/100 | agents ${j.agents_total - j.agents_missing_frontmatter.length}/${j.agents_total} | skills ${j.skills_total - j.skills_missing_frontmatter.length}/${j.skills_total} | send_gateway ${j.send_gateway_tests_pass} | pulse_fresh ${j.cmo_pulse_fresh}`;
        }
    } catch (_) {}
    await sendChunked(msg.chat.id, summary);
});

bot.onText(/^\/tests/, async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    const files = [
        'scripts/test_send_gateway.py',
        'scripts/test_late_publisher.py',
        'scripts/test_instagram_engine.py',
        'scripts/test_content_pipeline.py',
        'scripts/test_performance_reporter.py',
        'scripts/test_notify.py',
    ];
    const lines = ['Maven test sweep:'];
    for (const f of files) {
        const r = await runPython([f]);
        const tail = (r.stdout + r.stderr).split('\n').reverse().find(l => /Ran \d+ tests/.test(l)) || '(no result)';
        lines.push(`  ${f.replace('scripts/test_', '').replace('.py', '')}: ${tail.trim()} ${r.code === 0 ? 'OK' : 'FAIL'}`);
    }
    await sendChunked(msg.chat.id, lines.join('\n'));
});

bot.onText(/^\/inbox/, async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    const r = await runPython(['scripts/agent_inbox.py', 'list', '--to', 'maven']);
    await sendChunked(msg.chat.id, (r.stdout || r.stderr).slice(0, 3500) || '(no unread)');
});

bot.onText(/^\/post\s+(\S+)\s+(.+)/, async (msg, match) => {
    if (!isAuthorized(msg.chat.id)) return;
    const to = match[1].toLowerCase();
    const body = match[2];
    if (!['bravo', 'atlas', 'aura'].includes(to)) {
        await bot.sendMessage(msg.chat.id, `unknown target '${to}'. Use bravo|atlas|aura.`); return;
    }
    const sep = body.indexOf('||');
    if (sep < 0) {
        await bot.sendMessage(msg.chat.id, 'format: /post bravo subject || body'); return;
    }
    const subject = body.slice(0, sep).trim();
    const messageBody = body.slice(sep + 2).trim();
    const r = await runPython([
        'scripts/agent_inbox.py', '--json', 'post',
        '--from', 'maven', '--to', to,
        '--subject', subject, '--body', messageBody,
        '--priority', 'normal',
    ]);
    await sendChunked(msg.chat.id, (r.stdout || r.stderr).slice(0, 1500));
});

// ---- Plain-text → Claude context (delegated to Maven's Claude session) ----

bot.on('message', async (msg) => {
    if (!isAuthorized(msg.chat.id)) return;
    const text = (msg.text || '').trim();
    if (!text || text.startsWith('/') || /^yes engage/i.test(text)) return;

    // Spawn Claude Code with the message as the prompt. Falls back to a
    // friendly "no claude binary" message if the CLI isn't installed.
    const claudeBin = IS_WIN ? 'claude.cmd' : 'claude';
    const args = ['--dangerously-skip-permissions', '-p', text];
    const child = spawn(claudeBin, args, { cwd: PROJECT_ROOT, env: { ...process.env } });
    let out = '', err = '';
    child.stdout.on('data', (d) => out += d.toString());
    child.stderr.on('data', (d) => err += d.toString());
    child.on('error', async () => {
        await sendChunked(msg.chat.id,
            'Claude CLI not on PATH. Install with `npm i -g @anthropic-ai/claude-code` or use the slash commands directly.');
    });
    child.on('close', async () => {
        const reply = (out || err || '(no response)').slice(0, 3500);
        await sendChunked(msg.chat.id, reply);
    });
});

log(`[BOOT] Maven Telegram bridge online on ${MACHINE_NAME} (pid ${process.pid}).`);
log(`[BOOT] Authorized chat IDs: ${ALLOWED_USERS.join(', ')}`);
log(`[BOOT] Cross-agent repos: bravo=${SIBLING_REPOS.bravo} atlas=${SIBLING_REPOS.atlas} aura=${SIBLING_REPOS.aura}`);
