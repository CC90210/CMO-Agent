require('dotenv').config({ path: '.env.agents' });
const TelegramBot = require('node-telegram-bot-api');
const { spawn, exec, execFile } = require('child_process');
const fs = require('fs');
const path = require('path');

// ============================================================
// MAVEN TELEGRAM BRIDGE V1.0 (CMO Agent — 2026-04-26)
//
// Mirror of Bravo's V15.7 architecture (single source of truth via
// scripts/c_suite_context.js, tier classifier, IDE-parity Claude spawn,
// approval gate with inline buttons, file relay, voice transcription)
// adapted for Maven's marketing surface.
//
// V1.0 deltas vs Bravo:
//  - MAVEN_TELEGRAM_BOT_TOKEN + MAVEN_TELEGRAM_CHAT_ID env vars (distinct
//    bot — Maven, Bravo, Atlas never poll the same token).
//  - Maven-perspective sibling pulses: iterates [bravo, atlas, aura] via
//    a wrapper around c_suite_context's loadSiblingPulses (the module is
//    copied verbatim from Bravo and is Bravo-perspective by default; the
//    wrapper rewrites the perspective without touching the shared file).
//  - Marketing-tuned tool routing: ad creative, paid channels (Meta/Google),
//    organic (Late/Zernio + Instagram), email blasts, reporting.
//  - HARD CFO approval gate before any paid launch: reads cfo_pulse.json
//    via readSiblingRepo('atlas', ...), refuses on stale (>24h), shows
//    inline ✅/❌ buttons, logs cross-repo to Bravo + Atlas via agent_inbox.
//  - MAVEN_FORCE_DRY_RUN=1 short-circuits ALL outbound (mirrors send_gateway
//    killswitch).
// ============================================================

// ---- PLATFORM DETECTION ----
const IS_MAC = process.platform === 'darwin';
const IS_WIN = process.platform === 'win32';
const PYTHON = IS_MAC ? 'python3' : path.join(__dirname, '.venv', 'Scripts', 'python.exe');
const FALLBACK_PYTHON = IS_MAC ? 'python3' : 'python';
const MACHINE_NAME = IS_MAC ? 'MacBook' : 'Windows Desktop';
const TEMP_PATH = IS_MAC ? '/tmp' : (process.env.TEMP || 'C:\\Temp');

const TELEGRAM_TOKEN =
    process.env.MAVEN_TELEGRAM_BOT_TOKEN
    || process.env.TELEGRAM_BOT_TOKEN; // fallback for single-bot rigs
const MAVEN_CHAT_ID = (process.env.MAVEN_TELEGRAM_CHAT_ID || '').trim();
const LOG_FILE = path.join(__dirname, 'memory', 'telegram_bridge.log');
const LOCK_FILE = path.join(__dirname, 'tmp', 'maven_telegram.lock.json');

// ---- C-SUITE CROSS-AGENT MODULE ----
// Copied verbatim from Bravo (single source of truth — same file in both
// repos, byte-identical, exercised by scripts/test_c_suite_context.js).
// The module is Bravo-perspective by default. Maven uses SIBLING_REPOS +
// readSiblingRepo + readSelfRepo + loadCSuiteSnapshot directly, but
// rewrites loadSiblingPulses to a Maven-perspective wrapper below so the
// sibling list reads [bravo, atlas, aura] instead of [maven, atlas, aura].
const cSuite = require('./scripts/c_suite_context.js');
const { SIBLING_REPOS, SIBLING_CANDIDATES, readSiblingRepo } = cSuite;

const log = (msg) => {
    const line = `[${new Date().toISOString()}] ${msg}\n`;
    console.log(line.trim());
    try { fs.appendFileSync(LOG_FILE, line); } catch (_) {}
};

const ensureDirs = () => {
    for (const d of ['tmp', 'memory']) {
        try { fs.mkdirSync(path.join(__dirname, d), { recursive: true }); } catch (_) {}
    }
};

// ---- SINGLE-INSTANCE LOCK ----
const isPidAlive = (pid) => {
    if (!pid || Number.isNaN(Number(pid))) return false;
    try { process.kill(Number(pid), 0); return true; } catch (_) { return false; }
};

const acquireInstanceLock = () => {
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

const releaseInstanceLock = () => {
    try {
        if (!fs.existsSync(LOCK_FILE)) return;
        const existing = JSON.parse(fs.readFileSync(LOCK_FILE, 'utf8'));
        if (existing.pid === process.pid) fs.unlinkSync(LOCK_FILE);
    } catch (_) {}
};

// ---- BOOT VALIDATION ----
if (!TELEGRAM_TOKEN) {
    console.error('MAVEN_TELEGRAM_BOT_TOKEN missing in .env.agents.');
    console.error('Create a Maven-only bot via @BotFather, then add:');
    console.error('  MAVEN_TELEGRAM_BOT_TOKEN=<token>');
    console.error('  MAVEN_TELEGRAM_CHAT_ID=<your telegram user/chat id>');
    process.exit(1);
}

acquireInstanceLock();
process.on('exit', releaseInstanceLock);

// ── Multi-machine arbitration via scripts/bridge_lock.py ────────────────────
// Same pattern as Bravo: prevents Mac and Windows bridges from both polling
// the same Telegram token at once. Owner heartbeats every 15s; loser exits.
const BRIDGE_LOCK_AGENT = 'maven';
const BRIDGE_LOCK_SCRIPT = path.join(__dirname, 'scripts', 'bridge_lock.py');
// Resolve Python interpreter robustly. Try local venv first, then system python.
// Maven historically didn't have a project-local .venv; clients may or may not.
function _resolvePython() {
    const candidates = IS_MAC
        ? [path.join(__dirname, '.venv', 'bin', 'python'), 'python3', 'python']
        : [path.join(__dirname, '.venv', 'Scripts', 'python.exe'), 'python', 'python3'];
    for (const c of candidates) {
        if (c.includes('/') || c.includes('\\')) {
            try { if (fs.existsSync(c)) return c; } catch (_) {}
        } else {
            // bare name — let spawn resolve via PATH
            return c;
        }
    }
    return 'python';
}
const PYTHON_BIN = _resolvePython();
function bridgeLock(action) {
    try {
        const r = require('child_process').spawnSync(
            PYTHON_BIN, [BRIDGE_LOCK_SCRIPT, action, '--agent', BRIDGE_LOCK_AGENT, '--json'],
            {
                encoding: 'utf-8',
                timeout: 5000,
                // CRITICAL on Windows: without windowsHide, every spawnSync
                // pops a console window. Heartbeat at 15s would flash a window
                // every 15 seconds. Match Bravo's pattern: `windowsHide: IS_WIN`
                // (no-op on macOS, suppression on Windows).
                windowsHide: IS_WIN,
                shell: false,
            }
        );
        // r.status === null when spawn itself failed (ENOENT, missing python, etc.)
        // Treat that as "lock unverifiable" — log and proceed (don't block startup).
        if (r.status === null) {
            return { ok: true, status: -1, stdout: '', warn: `python not found (${PYTHON_BIN}); skipping multi-machine arbitration` };
        }
        return { ok: r.status === 0, status: r.status, stdout: (r.stdout || '').trim() };
    } catch (e) {
        // Same fallback: don't block bridge startup if subprocess can't run.
        return { ok: true, status: -1, stdout: '', warn: String(e).slice(0, 200) };
    }
}
const lockAcquire = bridgeLock('acquire');
if (!lockAcquire.ok) {
    log(`[BRIDGE-LOCK] CONFLICT — another machine owns Maven's bridge: ${lockAcquire.stdout || lockAcquire.error}`);
    log(`[BRIDGE-LOCK] Exiting with code 1 so PM2 backs off and retries when the other machine releases.`);
    process.exit(1);
}
if (lockAcquire.warn) {
    log(`[BRIDGE-LOCK] WARN: ${lockAcquire.warn}`);
}
log(`[BRIDGE-LOCK] Acquired (${BRIDGE_LOCK_AGENT}) — this machine now owns Maven's Telegram bridge.`);
setInterval(() => bridgeLock('heartbeat'), 15000);
process.on('exit', () => bridgeLock('release'));
process.on('SIGINT',  () => { bridgeLock('release'); process.exit(0); });
process.on('SIGTERM', () => { bridgeLock('release'); process.exit(0); });

const bot = new TelegramBot(TELEGRAM_TOKEN, {
    polling: { autoStart: false, params: { timeout: 30 } },
    request: { timeout: 60000 },
});

log(`Maven Telegram Bridge V1.0 (${IS_MAC ? 'macOS' : 'Windows'} - CMO surface) starting...`);

// ---- CONVERSATION HISTORY ----
const MAX_HISTORY = 15;
const HISTORY_FILE = path.join(__dirname, 'tmp', 'telegram_history.json');

let chatHistory = {};
try {
    if (fs.existsSync(HISTORY_FILE)) {
        chatHistory = JSON.parse(fs.readFileSync(HISTORY_FILE, 'utf8'));
        const n = Object.keys(chatHistory).length;
        if (n > 0) log(`[HISTORY] Loaded ${n} chat(s) from disk`);
    }
} catch (_) { chatHistory = {}; }

const saveHistory = () => {
    try { fs.writeFileSync(HISTORY_FILE, JSON.stringify(chatHistory)); } catch (_) {}
};

const addToHistory = (chatId, role, text) => {
    const id = String(chatId);
    if (!chatHistory[id]) chatHistory[id] = [];
    chatHistory[id].push({ role, text: (text || '').substring(0, 2000), ts: new Date().toISOString() });
    if (chatHistory[id].length > MAX_HISTORY) {
        chatHistory[id] = chatHistory[id].slice(-MAX_HISTORY);
    }
    saveHistory();
};

const getHistoryBlock = (chatId) => {
    const id = String(chatId);
    const msgs = chatHistory[id];
    if (!msgs || msgs.length === 0) return '';
    return '\n=== RECENT CONVERSATION HISTORY ===\n' +
        msgs.map(m => `[${m.role.toUpperCase()}]: ${m.text}`).join('\n') +
        '\n=== END HISTORY ===\n';
};

// ---- RATE LIMITING ----
const RATE_LIMIT_WINDOW = 10000;
const RATE_LIMIT_MAX = 5;
const rateLimitMap = {};

// ---- AUTHORIZATION ----
const ENV_FILE = path.join(__dirname, '.env.agents');
let ALLOWED_USERS = [
    ...((process.env.MAVEN_TELEGRAM_ALLOWED_USERS || '').split(',').map(s => s.trim()).filter(Boolean)),
    ...((process.env.TELEGRAM_ALLOWED_USERS || '').split(',').map(s => s.trim()).filter(Boolean)),
];
if (MAVEN_CHAT_ID && !ALLOWED_USERS.includes(MAVEN_CHAT_ID)) ALLOWED_USERS.push(MAVEN_CHAT_ID);
ALLOWED_USERS = [...new Set(ALLOWED_USERS)];

const autoRegisterUser = (userId) => {
    try {
        let envContent = fs.readFileSync(ENV_FILE, 'utf8');
        if (envContent.includes('MAVEN_TELEGRAM_CHAT_ID=')) {
            envContent = envContent.replace(/MAVEN_TELEGRAM_CHAT_ID=.*/, `MAVEN_TELEGRAM_CHAT_ID=${userId}`);
        } else {
            envContent += `\nMAVEN_TELEGRAM_CHAT_ID=${userId}\n`;
        }
        fs.writeFileSync(ENV_FILE, envContent);
        ALLOWED_USERS = [String(userId)];
        log(`[SECURITY] Auto-registered Maven owner: ${userId}. All other users now blocked.`);
    } catch (e) {
        log(`[SECURITY] Failed to save user ID: ${e.message}`);
    }
};

// ---- KILLSWITCH ----
const KILLSWITCH_ENGAGED = () => /^(1|true|yes|on)$/i.test(String(process.env.MAVEN_FORCE_DRY_RUN || ''));

// ---- C-SUITE HELPERS — Maven perspective ----
//
// loadCSuiteSnapshot from the shared module is canonical (reads
// CROSS_AGENT_AWARENESS.md from Bravo's repo via readSelfRepo). We use
// SIBLING_REPOS so it points at Bravo regardless of where Maven is
// running, which is correct — the canonical doc lives in Bravo.
const loadCSuiteSnapshot = () => cSuite.loadCSuiteSnapshot({ python: PYTHON });
const loadLocalSiblingPaths = () => cSuite.loadLocalSiblingPaths({ machineName: MACHINE_NAME });

// Maven-perspective sibling pulses: list [bravo, atlas, aura] (NOT maven).
// Mirrors the shared module's logic but with the right perspective.
const formatAge = (iso, now = Date.now()) => {
    if (!iso) return 'unknown';
    const t = new Date(iso).getTime();
    if (Number.isNaN(t)) return 'unknown';
    const ageMs = now - t;
    if (ageMs < 0) return 'future';
    if (ageMs < 60000) return 'just now';
    const m = Math.floor(ageMs / 60000);
    if (m < 60) return `${m}m ago`;
    const h = Math.floor(m / 60);
    if (h < 24) return `${h}h ago`;
    return `${Math.floor(h / 24)}d ago`;
};

const loadMavenSiblingPulses = (opts = {}) => {
    const staleHours = opts.staleHours || 24;
    const now = opts.now || Date.now();
    const lines = ['=== SIBLING PULSES (current state of Bravo/Atlas/Aura — Maven perspective) ==='];
    const targets = [
        ['bravo', 'ceo_pulse.json', 'CEO'],
        ['atlas', 'cfo_pulse.json', 'CFO'],
        ['aura',  'aura_pulse.json', 'Life'],
    ];
    for (const [agent, file, role] of targets) {
        const raw = readSiblingRepo(agent, `data/pulse/${file}`);
        if (!raw) {
            lines.push(`- ${agent.toUpperCase()} (${role}): pulse not reachable`);
            continue;
        }
        try {
            const pulse = JSON.parse(raw);
            const note = (pulse.session_note || pulse.note || pulse.last_note || '').trim().slice(0, 200);
            const tsField = pulse.updated_at || pulse.timestamp;
            const age = formatAge(tsField, now);
            const tsMs = new Date(tsField || 0).getTime();
            const stale = Number.isNaN(tsMs) || (now - tsMs) > staleHours * 3600000;
            const flag = stale ? ' ⚠ STALE' : '';
            lines.push(`- ${agent.toUpperCase()} (${role}, ${age}${flag}): ${note || '(no session_note)'}`);
        } catch (_) {
            lines.push(`- ${agent.toUpperCase()} (${role}): pulse exists but failed to parse`);
        }
    }
    return lines.join('\n');
};

// Read a file from Maven's own repo (correct self-resolution — the shared
// module's readSelfRepo returns Bravo's content because the module is
// Bravo-perspective). For Maven self reads, use this wrapper.
const readMavenRepo = (relPath, maxLines = 0) => {
    return readSiblingRepo('maven', relPath, maxLines);
};

// ---- CFO SPEND-GATE READER (HARD GATE FOR PAID LAUNCHES) ----
const readCfoPulse = () => {
    const raw = readSiblingRepo('atlas', 'data/pulse/cfo_pulse.json');
    if (!raw) return { ok: false, reason: 'cfo_pulse.json not reachable from Maven' };
    try {
        const pulse = JSON.parse(raw);
        const tsField = pulse.updated_at || (pulse.spend_gate || {}).updated_at;
        if (!tsField) return { ok: false, reason: 'cfo_pulse.json missing updated_at', pulse };
        const ageHours = (Date.now() - new Date(tsField).getTime()) / 3600000;
        if (Number.isNaN(ageHours)) return { ok: false, reason: 'cfo_pulse.json updated_at unparseable', pulse };
        if (ageHours > 24) return { ok: false, reason: `cfo_pulse stale (${ageHours.toFixed(1)}h > 24h)`, pulse, ageHours };
        const sg = pulse.spend_gate || {};
        if (sg.status !== 'open') return { ok: false, reason: `Atlas spend gate status=${sg.status}`, pulse };
        return { ok: true, pulse, ageHours };
    } catch (e) {
        return { ok: false, reason: `cfo_pulse parse error: ${e.message}` };
    }
};

const summarizeCfoApproval = (pulse, channel, brand) => {
    const sg = pulse.spend_gate || {};
    const approvals = sg.approvals || {};
    const channelBlock = approvals[channel] || {};
    const brandBlock = channelBlock[brand] || channelBlock['*'];
    if (!brandBlock) return null;
    return {
        daily_budget_usd: brandBlock.daily_budget_usd,
        wildcard: !channelBlock[brand] && !!channelBlock['*'],
    };
};

// ---- TIER CLASSIFICATION (marketing-tuned for Maven) ----
const T1_KEYWORDS = ['status', 'check', 'what', 'how much', 'count', 'list', 'show', 'hello', 'hey', 'hi', 'thanks'];
const T3_KEYWORDS = ['strategy', 'rebrand', 'audience research', 'competitive analysis', 'redesign', 'architecture', 'overhaul'];
// T0: marketing quick-actions that need minimal context
const T0_KEYWORDS = /\b(post|tweet|campaign|ad|creative|headline|report|roas|cpl|ctr|cpc|cpm|spend|budget|image|video|thumbnail|caption|reel|short|carousel|email blast|dm|story|hook|pillar|ideation|publish|schedule|cross.?post)\b/i;
// Coding-task verbs that indicate T2 even if T0 keywords are present
const T0_CODING_EXCLUSIONS = /\b(fix|debug|implement|refactor|build feature|write code|write function|failing test|unit test|create api|create endpoint|create route|create table|create schema)\b/i;

const classifyTier = (text) => {
    const t = (text || '').toLowerCase();
    if (T0_KEYWORDS.test(t) && !T3_KEYWORDS.some(k => t.includes(k)) && !T0_CODING_EXCLUSIONS.test(t)) return 0;
    if (T3_KEYWORDS.some(k => t.includes(k))) return 3;
    const hasActionVerb = /\b(build|fix|implement|create|update|add|modify|debug|test|deploy|write|change|edit|push|ship|review)\b/.test(t);
    if (!hasActionVerb && T1_KEYWORDS.some(k => t.includes(k))) return 1;
    return 2;
};

// ---- PAID-LAUNCH DETECTION ----
// Maven's bridge intercepts these BEFORE Claude spawn so we can run the
// hard CFO gate. If a user message matches, we read cfo_pulse, verify
// approval, show inline ✅/❌ buttons; only on ✅ do we call Claude.
const PAID_LAUNCH_PATTERN = /\b(launch|start|spin up|run|kick off|deploy|publish|send)\b.{0,80}\b(meta|facebook|instagram ads|google ads|email blast|newsletter|paid|campaign|spend)\b/i;

// Pending paid-launch confirmations: chatId -> {description, channel, brand, amount, ts}
const PENDING_PAID = {};

// ---- TOOL ROUTING (MARKETING-TUNED) ----
const buildMavenToolBlock = () => `=== MAVEN TOOL ROUTING (marketing surface) ===

CONTENT + CREATIVE:
- Generate ideas:    ${PYTHON} scripts/script_ideation.py generate --count N [--pillar X] [--format short_video|long_video|post|carousel] [--topic "..."]
- Generate ad image: ${PYTHON} scripts/imagen_generate.py "<prompt>"
- Codex image:       ${PYTHON} scripts/codex_image_gen.py generate "<prompt>" [--style branded|quote|thumbnail|carousel|split|raw]
- Render video:      ${PYTHON} scripts/render_video.py <template>
- Full pipeline:     ${PYTHON} scripts/content_pipeline.py <video.mp4>
- Ad copy variants:  ${PYTHON} scripts/ad_copy_generator.py "<topic>" --count 5

PAID CHANNELS — HARD-GATED through Atlas's cfo_pulse.json:
- Meta launch:    ${PYTHON} scripts/meta_ads_engine.py launch <campaign>
- Google launch:  ${PYTHON} scripts/google_ads_engine.py launch <campaign>
- Meta status:    ${PYTHON} scripts/meta_ads_engine.py status
- Google status:  ${PYTHON} scripts/google_ads_engine.py status
The bridge READS cfo_pulse before any launch. Refuses on stale (>24h).
Approval prompt is shown to CC; only ✅ proceeds. ❌ logs and drops.

ORGANIC + SOCIAL:
- Schedule post:  ${PYTHON} scripts/late_publisher.py publish-due
- Cross-post:    ${PYTHON} scripts/late_tool.py cross-post --text "..." --profile <id>
- Late accounts: ${PYTHON} scripts/late_tool.py accounts
- Late posts:    ${PYTHON} scripts/late_tool.py posts --status published --json
- IG DMs:        ${PYTHON} scripts/instagram_engine.py check-dms
- Email blast:   ${PYTHON} scripts/email_blast.py send <list> <template>

REPORTING + EXPERIMENTS:
- Performance:   ${PYTHON} scripts/performance_reporter.py weekly --json
- A/B test:      ${PYTHON} scripts/ab_testing_engine.py status
- Self-audit:    ${PYTHON} scripts/self_audit.py --json

CROSS-AGENT (file reads + inbox):
- Read CFO pulse: cat ${SIBLING_REPOS.atlas}/data/pulse/cfo_pulse.json
- Read CEO pulse: cat ${SIBLING_REPOS.bravo}/data/pulse/ceo_pulse.json
- Post to Bravo: ${PYTHON} scripts/agent_inbox.py post --from maven --to bravo --subject "..." --body "..."
- Post to Atlas: ${PYTHON} scripts/agent_inbox.py post --from maven --to atlas --subject "..." --body "..."
- Post to Aura:  ${PYTHON} scripts/agent_inbox.py post --from maven --to aura  --subject "..." --body "..."
- Inbox list:    ${PYTHON} scripts/agent_inbox.py list --to maven

KILLSWITCH:
- MAVEN_FORCE_DRY_RUN=1 short-circuits ALL outbound at the send_gateway.
- Currently: ${KILLSWITCH_ENGAGED() ? '🔒 ENGAGED — no real sends' : 'OFF — sends are live'}
`;

// ---- CONTEXT LOADER (tier-aware) ----
const loadContext = (tier = 2) => {
    const chunks = [];

    const state = readMavenRepo('brain/STATE.md');
    if (state) chunks.push(`=== STATE.md ===\n${state}`);

    const tasks = readMavenRepo('memory/ACTIVE_TASKS.md', 50);
    if (tasks) chunks.push(`=== ACTIVE_TASKS.md ===\n${tasks}`);

    if (tier === 1) {
        chunks.push(`=== Context Tier: T1 MINIMAL (status query) ===`);
        return chunks.join('\n\n');
    }

    chunks.push(loadCSuiteSnapshot());
    chunks.push(loadLocalSiblingPaths());
    chunks.push(loadMavenSiblingPulses());

    const claudeMd = readMavenRepo('CLAUDE.md');
    if (claudeMd) chunks.push(`=== CLAUDE.md ===\n${claudeMd}`);

    const soul = readMavenRepo('brain/SOUL.md', 40);
    if (soul) chunks.push(`=== SOUL.md ===\n${soul}`);

    // T2+ pulls Marketing Canon + Responsibility Boundaries + recent SESSION_LOG
    const canon = readMavenRepo('brain/MARKETING_CANON.md', 80);
    if (canon) chunks.push(`=== MARKETING_CANON.md (top 80 lines) ===\n${canon}`);

    const boundaries = readMavenRepo('brain/RESPONSIBILITY_BOUNDARIES.md');
    if (boundaries) chunks.push(`=== RESPONSIBILITY_BOUNDARIES.md ===\n${boundaries}`);

    const sessionLog = readMavenRepo('memory/SESSION_LOG.md');
    if (sessionLog) {
        const lastN = sessionLog.split('\n').slice(tier === 3 ? -50 : -30).join('\n').trim();
        if (lastN) chunks.push(`=== SESSION_LOG.md (last 30) ===\n${lastN}`);
    }

    chunks.push(buildMavenToolBlock());

    if (tier === 2) {
        chunks.push(`=== Context Tier: T2 STANDARD ===`);
        const full = chunks.join('\n\n');
        return full.length > 8000 ? full.substring(0, 8000) + '\n...(truncated)' : full;
    }

    // T3 — full context
    const agents = readMavenRepo('brain/AGENTS.md', 80);
    if (agents) chunks.push(`=== AGENTS.md ===\n${agents}`);

    const contentBible = readMavenRepo('brain/CONTENT_BIBLE.md');
    if (contentBible) chunks.push(`=== CONTENT_BIBLE.md ===\n${contentBible}`);

    const videoBible = readMavenRepo('brain/VIDEO_PRODUCTION_BIBLE.md', 60);
    if (videoBible) chunks.push(`=== VIDEO_PRODUCTION_BIBLE.md (top 60) ===\n${videoBible}`);

    chunks.push(`=== Context Tier: T3 FULL ===`);
    const full = chunks.join('\n\n');
    return full.length > 12000 ? full.substring(0, 12000) + '\n...(truncated)' : full;
};

// ---- PROMPT BUILDER ----
const buildPrompt = (chatId, userText = '') => {
    const tier = classifyTier(userText);
    const history = getHistoryBlock(chatId);
    log(`[TIER] T${tier} — ${tier === 0 ? 'QUICK' : tier === 1 ? 'minimal' : tier === 2 ? 'standard' : 'full'}`);

    if (tier === 0) {
        const csuite = loadCSuiteSnapshot();
        const reach = loadLocalSiblingPaths();
        const pulses = loadMavenSiblingPulses();
        return `You are MAVEN (CMO agent in CC's 4-agent C-Suite), running on his ${MACHINE_NAME}. Marketing surface: ad creative, paid campaigns, organic, email blasts, brand voice. Be direct, no filler.

${csuite}

${reach}

${pulses}

${buildMavenToolBlock()}
${history}
RULES:
(1) Answer in 1-5 sentences unless task requires more.
(2) Brand voice: ${readMavenRepo('media/brand/BRAND_GUIDE.md', 8) || 'see BRAND_GUIDE'}
(3) Cite at least one framework from MARKETING_CANON when recommending creative or strategy.
(4) Paid launches go through the bridge's CFO gate — DO NOT bypass.
(5) Refer to CC by name. Direct, no filler.
(6) Address user as CC. ${KILLSWITCH_ENGAGED() ? 'KILLSWITCH ENGAGED — no real sends.' : ''}

CC's message:`;
    }

    const context = loadContext(tier);
    return `You are MAVEN V1.4 (CMO agent in CC's 4-agent C-Suite), CC's marketing operations engine, running via Telegram.
You have full access to the CMO-Agent project at ${__dirname}.
Platform: ${IS_MAC ? 'macOS' : 'Windows'} — Machine: ${MACHINE_NAME}
You own: ad creative, paid (Meta + Google), organic (Late/Zernio + IG), funnels, email blasts, content pipeline, brand voice, attribution.
You DO NOT own: cold outreach (Bravo), client relationships (Bravo), trade execution (Atlas), tax/runway (Atlas), home automation (Aura).
Sibling repos are reachable from this machine — see SIBLING REACHABILITY block. You CAN read them.

${context}
${history}
RULES:
(1) Answer directly in 1-5 sentences unless task requires depth.
(2) Use the tool routing above. ${PYTHON} for all script calls.
(3) Cite MARKETING_CANON entries when making creative or strategy recommendations.
(4) Paid launches: bridge has already gated cfo_pulse if this prompt got through; you may proceed.
(5) After significant work, update memory/SESSION_LOG.md and brain/STATE.md (state_sync runs after T1+ runs).
(6) Output "⚠️ CONFIRM: <description>" before destructive actions and STOP — bridge intercepts and asks CC.
(7) Speak like CC's BRAND_GUIDE: confident-not-arrogant, direct-not-corporate. NO hustle/synergy/leverage/10x language.
(8) ${KILLSWITCH_ENGAGED() ? 'MAVEN_FORCE_DRY_RUN engaged — DO NOT execute real sends.' : 'Killswitch off; real sends OK if other gates pass.'}

CC's message:`;
};

// ---- APPROVAL GATE (destructive actions) ----
const CONFIRM_PATTERN = /⚠️\s*CONFIRM:\s*(.+)$/m;
const PENDING_CONFIRMATIONS = {};

setInterval(() => {
    const now = Date.now();
    for (const [chatId, p] of Object.entries(PENDING_CONFIRMATIONS)) {
        if (now - p.timestamp > 300000) delete PENDING_CONFIRMATIONS[chatId];
    }
    for (const [chatId, p] of Object.entries(PENDING_PAID)) {
        if (now - p.ts > 300000) delete PENDING_PAID[chatId];
    }
}, 300000);

// ---- CHILD-PROCESS TRACKING ----
const activeChildren = new Set();
const killTree = (pid) => {
    try {
        if (IS_WIN) spawn('taskkill', ['/pid', String(pid), '/T', '/F'], { windowsHide: true, stdio: 'ignore', shell: false });
        else process.kill(pid, 'SIGKILL');
    } catch (_) {}
};

// ---- CLI EXECUTION (Claude CLI primary + direct Anthropic API fallback) ----
const NODE_EXE = process.execPath;
const CLAUDE_EXE = IS_MAC
    ? 'claude'
    : path.join(process.env.USERPROFILE || '', '.local', 'bin', 'claude.exe');
const CLAUDE_TIMEOUT = 600000;
const T0_TIMEOUT = 300000;
const MCP_CONFIG_PATH = path.join(__dirname, '.claude', 'mcp.json');
const HAS_MCP_CONFIG = fs.existsSync(MCP_CONFIG_PATH);

// Patterns that indicate the CLI failed due to subscription/auth — triggering
// automatic fallback to the direct Anthropic API using ANTHROPIC_API_KEY.
const CLI_FALLBACK_TRIGGERS = /out of (extra )?usage|usage limit|subscription.*limit|plan limit|rate.?limit exceeded|authentication_error|OAuth.*expired|401|Invalid API key|ENOENT|spawn.*ENOENT|could not find/i;

const cleanOutput = (raw) => {
    let text = (raw || '')
        .replace(/[\x1b][[()#;?]*(?:[0-9]{1,4}(?:;[0-9]{0,4})*)?[0-9A-ORZcf-nqry=><]/g, '')
        .replace(/[⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏]/g, '');
    const noise = [
        /^[█▓░▀▄▐▌]+/,
        /logged in with/i,
        /waiting for mcp/i,
        /^Loading/i,
        /Loaded cached credentials/i,
        /^\s*$/,
    ];
    return text.split('\n').filter(line => !noise.some(p => p.test(line.trim()))).join('\n').trim() || text.trim();
};

// ---- DIRECT ANTHROPIC API FALLBACK ----
// Uses ANTHROPIC_API_KEY from .env.agents to call the Messages API directly.
// This is independent of the Claude CLI subscription and serves as a reliable
// fallback when the CLI is unavailable or out of usage.
const executeAnthropicDirect = (userPrompt, chatId, modelOverride = null) => {
    return new Promise((resolve) => {
        const https = require('https');
        const apiKey = process.env.ANTHROPIC_API_KEY;

        if (!apiKey) {
            log('[FALLBACK] ANTHROPIC_API_KEY missing — cannot use direct API fallback');
            resolve('Both Claude CLI and direct API unavailable. Add ANTHROPIC_API_KEY to .env.agents.');
            return;
        }

        const tier = classifyTier(userPrompt);
        const systemPrompt = buildPrompt(chatId, userPrompt);
        // Model hierarchy: explicit override > tier-appropriate default
        const modelMap = { opus: 'claude-sonnet-4-20250514', sonnet: 'claude-sonnet-4-20250514', haiku: 'claude-haiku-4-5-20251001' };
        const model = modelOverride ? (modelMap[modelOverride] || 'claude-sonnet-4-20250514') : 'claude-sonnet-4-20250514';
        const maxTokens = tier <= 1 ? 2048 : 4096;

        log(`[FALLBACK] Direct Anthropic API: model=${model} tier=T${tier} prompt=${userPrompt.substring(0, 60)}...`);

        const body = JSON.stringify({
            model,
            max_tokens: maxTokens,
            system: systemPrompt,
            messages: [{ role: 'user', content: userPrompt }],
        });

        const req = https.request({
            hostname: 'api.anthropic.com',
            path: '/v1/messages',
            method: 'POST',
            headers: {
                'x-api-key': apiKey,
                'anthropic-version': '2023-06-01',
                'content-type': 'application/json',
                'content-length': Buffer.byteLength(body),
            },
            timeout: tier === 0 ? T0_TIMEOUT : CLAUDE_TIMEOUT,
        }, (res) => {
            let responseBody = '';
            res.on('data', d => responseBody += d.toString());
            res.on('end', () => {
                if (res.statusCode === 200) {
                    try {
                        const parsed = JSON.parse(responseBody);
                        const text = (parsed.content || []).map(c => c.text || '').join('\n').trim();
                        log(`[FALLBACK] Success: ${text.length} chars, model=${parsed.model || model}`);

                        // state_sync after successful T1+ runs
                        if (tier > 0) {
                            execFile(PYTHON, ['scripts/state_sync.py', '--note', `telegram-api T${tier}: ${userPrompt.substring(0, 140)}`],
                                { cwd: __dirname, windowsHide: true, timeout: 8000 }, () => {});
                        }

                        resolve(text || 'Done.');
                    } catch (e) {
                        log(`[FALLBACK] Parse error: ${e.message}`);
                        resolve(responseBody.substring(0, 3000) || 'API returned unparseable response.');
                    }
                } else {
                    log(`[FALLBACK] API HTTP ${res.statusCode}: ${responseBody.substring(0, 500)}`);
                    let errMsg = `API error (HTTP ${res.statusCode})`;
                    try {
                        const errJson = JSON.parse(responseBody);
                        errMsg = errJson.error?.message || errMsg;
                    } catch (_) {}
                    resolve(`Direct API fallback also failed: ${errMsg}`);
                }
            });
        });

        req.on('timeout', () => {
            log('[FALLBACK] Request timed out');
            req.destroy();
            resolve('Direct API fallback timed out.');
        });

        req.on('error', (e) => {
            log(`[FALLBACK] Request error: ${e.message}`);
            resolve(`Direct API fallback error: ${e.message}`);
        });

        // Keep-alive typing indicator
        const typing = setInterval(() => {
            if (chatId) bot.sendChatAction(chatId, 'typing').catch(() => {});
        }, 8000);
        req.on('close', () => clearInterval(typing));

        req.write(body);
        req.end();
    });
};

const executeClaude = (userPrompt, chatId, modelOverride = null) => {
    return new Promise((resolve) => {
        const tier = classifyTier(userPrompt);
        const fullPrompt = `${buildPrompt(chatId, userPrompt)} ${userPrompt}`;
        const timeout = tier === 0 ? T0_TIMEOUT : CLAUDE_TIMEOUT;
        const args = [
            '-p', fullPrompt,
            '--permission-mode', 'acceptEdits',
            '--output-format', 'text',
            '--max-turns', tier === 0 ? '6' : '25',
            '--setting-sources', 'project,local',
        ];
        if (HAS_MCP_CONFIG) args.push('--mcp-config', MCP_CONFIG_PATH);
        if (modelOverride) args.push('--model', modelOverride);

        log(`[EXEC] claude CLI T${tier}: "${userPrompt.substring(0, 80)}..."`);

        const child = spawn(CLAUDE_EXE, args, {
            env: { ...process.env, CI: 'true', NONINTERACTIVE: 'true', PAGER: 'cat', NO_COLOR: '1', FORCE_COLOR: '0' },
            stdio: ['ignore', 'pipe', 'pipe'],
            shell: false,
            windowsHide: true,
            cwd: __dirname,
        });
        activeChildren.add(child);

        let stdout = '', stderr = '';
        child.stdout.on('data', d => stdout += d.toString());
        child.stderr.on('data', d => stderr += d.toString());
        const start = Date.now();

        const progress = setInterval(() => {
            if (chatId) {
                const elapsed = Math.round((Date.now() - start) / 1000);
                bot.sendChatAction(chatId, 'typing').catch(() => {});
                if (elapsed >= 120 && elapsed % 120 === 0) {
                    bot.sendMessage(chatId, `Still working... (${elapsed}s)`).catch(() => {});
                }
            }
        }, 15000);

        const timer = setTimeout(() => {
            log(`[TIMEOUT] claude killed after ${timeout / 1000}s`);
            if (child.pid) killTree(child.pid);
            const partial = cleanOutput(stdout.trim());
            if (partial && partial.length > 20) resolve(`(Partial — timed out after ${timeout / 1000}s)\n\n${partial}`);
            else resolve(`Timed out after ${timeout / 1000}s.`);
        }, timeout);

        child.on('close', async (code) => {
            clearTimeout(timer);
            clearInterval(progress);
            activeChildren.delete(child);
            const elapsed = Math.round((Date.now() - start) / 1000);
            log(`[DONE] claude CLI code=${code} stdout=${stdout.length}b time=${elapsed}s`);

            const raw = (stdout.trim() || stderr.trim());

            // ---- FALLBACK CHECK: CLI subscription exhausted or auth failed ----
            if (code !== 0 && CLI_FALLBACK_TRIGGERS.test(raw + ' ' + stderr)) {
                log(`[FALLBACK] CLI failed with subscription/auth issue — switching to direct Anthropic API`);
                if (chatId) {
                    bot.sendMessage(chatId, '⚡ CLI subscription limit hit — switching to API key...').catch(() => {});
                }
                const apiResult = await executeAnthropicDirect(userPrompt, chatId, modelOverride);
                resolve(apiResult);
                return;
            }

            // state_sync after successful T1+ runs
            if (code === 0 && tier > 0) {
                execFile(PYTHON, ['scripts/state_sync.py', '--note', `telegram T${tier}: ${userPrompt.substring(0, 140)}`],
                    { cwd: __dirname, windowsHide: true, timeout: 8000 }, () => {});
            }

            if (!raw) {
                resolve(code === 0 ? 'Done.' : `Error (code ${code}).`);
                return;
            }
            resolve(cleanOutput(raw));
        });

        child.on('error', async (err) => {
            clearTimeout(timer);
            clearInterval(progress);
            activeChildren.delete(child);
            log(`[ERROR] claude CLI: ${err.message}`);

            // CLI binary not found or spawn error — fallback to direct API
            if (CLI_FALLBACK_TRIGGERS.test(err.message)) {
                log(`[FALLBACK] CLI not available — switching to direct Anthropic API`);
                if (chatId) {
                    bot.sendMessage(chatId, '⚡ CLI unavailable — switching to API key...').catch(() => {});
                }
                const apiResult = await executeAnthropicDirect(userPrompt, chatId, modelOverride);
                resolve(apiResult);
                return;
            }
            resolve(`Error: ${err.message}`);
        });
    });
};

// ---- CFO GATE FLOW (paid-launch hard gate) ----
const handlePaidLaunch = async (chatId, text) => {
    const cfoCheck = readCfoPulse();

    // Stale or unreachable → refuse + post to Atlas
    if (!cfoCheck.ok) {
        const reason = cfoCheck.reason;
        log(`[CFO GATE] Refusing paid launch: ${reason}`);
        await bot.sendMessage(chatId,
            `🚫 Paid launch REFUSED — Atlas spend gate not satisfied.\n\nReason: ${reason}\n\nMaven posted a heads-up to Atlas's inbox. Try again after Atlas refreshes the pulse.`);
        // Cross-repo notify Atlas
        execFile(PYTHON, [
            'scripts/agent_inbox.py', 'post',
            '--from', 'maven', '--to', 'atlas',
            '--priority', 'high',
            '--subject', 'Maven refused paid launch — pulse not satisfied',
            '--body', `Maven Telegram bridge refused a paid-launch attempt because: ${reason}\n\nUser request: ${text.substring(0, 300)}\nPlease refresh cfo_pulse.json or address the underlying state.`,
        ], { cwd: __dirname, windowsHide: true, timeout: 10000 }, () => {});
        return;
    }

    // Pulse OK — surface approval prompt with inline buttons
    const sg = cfoCheck.pulse.spend_gate || {};
    const approvalsBlock = JSON.stringify(sg.approvals || {}, null, 2).substring(0, 1000);
    const ageStr = `${cfoCheck.ageHours.toFixed(1)}h ago`;

    PENDING_PAID[String(chatId)] = {
        description: text.substring(0, 500),
        ts: Date.now(),
    };

    await bot.sendMessage(chatId,
        `🔒 Paid launch detected — verifying CFO approval.\n\n` +
        `Atlas spend gate: ${sg.status}\n` +
        `Last refreshed: ${ageStr}\n\n` +
        `Approvals:\n\`\`\`\n${approvalsBlock}\n\`\`\`\n\n` +
        `Request: "${text.substring(0, 200)}"\n\nProceed?`,
        {
            parse_mode: 'Markdown',
            reply_markup: {
                inline_keyboard: [[
                    { text: '✅ Launch', callback_data: 'paid_yes' },
                    { text: '❌ Cancel', callback_data: 'paid_no' },
                ]],
            },
        });
};

// ---- TELEGRAM HANDLER ----
bot.on('message', async (msg) => {
    pollErrorCount = 0;
    const chatId = msg.chat.id;
    const text = msg.text;
    if (!text) return;

    const userId = String(msg.from.id);
    const user = msg.from.username || msg.from.first_name || '?';

    // Auto-register first user, block all others
    if (ALLOWED_USERS.length === 0) {
        autoRegisterUser(userId);
        log(`[SECURITY] First user registered: ${user} (${userId})`);
    } else if (!ALLOWED_USERS.includes(userId)) {
        log(`[BLOCKED] Unauthorized user: ${user} (${userId})`);
        return bot.sendMessage(chatId, 'Unauthorized.').catch(() => {});
    }

    // Rate limiting
    const now = Date.now();
    if (!rateLimitMap[userId]) rateLimitMap[userId] = [];
    rateLimitMap[userId] = rateLimitMap[userId].filter(t => now - t < RATE_LIMIT_WINDOW);
    if (rateLimitMap[userId].length >= RATE_LIMIT_MAX) {
        log(`[RATE] Throttled ${user}`);
        return bot.sendMessage(chatId, 'Slow down — max 5 messages per 10 seconds.').catch(() => {});
    }
    rateLimitMap[userId].push(now);

    log(`[MSG] ${user} (${userId}): ${text}`);

    // ---- HELP / SLASH COMMANDS ----
    if (text === '/start' || text === '/help') {
        return bot.sendMessage(chatId, [
            `Maven CMO Bridge V1.0 (${MACHINE_NAME})`,
            '',
            'Just type → Claude handles it via Maven\'s marketing surface.',
            '',
            'TYPICAL ASKS:',
            '  "What\'s our ad spend this week?" → reads cfo_pulse + platform APIs',
            '  "Generate 5 ideas about Bennett rev share" → script_ideation',
            '  "Post a tweet about today\'s Bennett win" → drafts via critic, asks approval',
            '  "Launch the new creative on Meta" → CFO gate → ✅/❌ buttons',
            '',
            'SLASH COMMANDS:',
            '  /status — pulse status across Bravo/Atlas/Aura/Maven',
            '  /pulses — 3-agent C-suite snapshot (Bravo + Atlas + Maven)',
            '  /sibling <agent> [file] — read a sibling\'s brain/*.md',
            '  /spend  — Atlas spend-gate summary',
            '  /campaigns — send_gateway daily stats',
            '  /killswitch / /unleash — engage / disengage MAVEN_FORCE_DRY_RUN',
            '  /pulse  — refresh cmo_pulse.json',
            '  /sync   — full state_sync',
            '  /audit  — health score',
            '  /tests  — run all 6 test files, report pass/fail',
            '  /inbox  — unread agent_inbox messages addressed to maven',
            '  /post bravo|atlas|aura subject || body — cross-repo post',
            '  /clear  — clear conversation history',
            '  /whoami — show your Telegram user ID',
            '',
            `Killswitch: ${KILLSWITCH_ENGAGED() ? '🔒 ENGAGED' : 'OFF'}`,
        ].join('\n'));
    }

    if (text === '/whoami') {
        return bot.sendMessage(chatId, `User ID: ${userId}\nUsername: ${user}\nChat ID: ${chatId}`);
    }

    // /ping — fast bridge-only health check. Parity with Bravo + Atlas.
    if (text === '/ping') {
        const uptime = Math.round(process.uptime());
        return bot.sendMessage(chatId, `pong — Maven bridge alive (uptime ${uptime}s)`);
    }

    if (text === '/clear') {
        chatHistory[String(chatId)] = [];
        saveHistory();
        return bot.sendMessage(chatId, 'Conversation history cleared.');
    }

    if (text === '/status') {
        const lines = [
            `Maven bridge — ${MACHINE_NAME} (${process.platform})`,
            `Killswitch: ${KILLSWITCH_ENGAGED() ? '🔒 ENGAGED' : 'OFF'}`,
            '',
            loadMavenSiblingPulses(),
        ];
        return bot.sendMessage(chatId, lines.join('\n'));
    }

    // /pulses — 3-agent C-suite snapshot with role-specific headlines.
    // Atlas-V3.2 parity: each agent gets the field that matters for its role.
    if (text === '/pulses') {
        const out = ['3-Agent Pulse Snapshot'];
        const targets = [
            { label: 'Bravo (CEO)', agent: 'bravo', file: 'data/pulse/ceo_pulse.json' },
            { label: 'Atlas (CFO)', agent: 'atlas', file: 'data/pulse/cfo_pulse.json' },
            { label: 'Maven (CMO)', agent: 'maven', file: 'data/pulse/cmo_pulse.json' },
        ];
        for (const t of targets) {
            const raw = t.agent === 'maven'
                ? (() => { try { return fs.readFileSync(path.join(__dirname, t.file), 'utf8'); } catch (_) { return ''; } })()
                : readSiblingRepo(t.agent, t.file);
            if (!raw) { out.push(`  ${t.label}: MISSING`); continue; }
            let p; try { p = JSON.parse(raw); } catch (_) { out.push(`  ${t.label}: PARSE ERROR`); continue; }
            const age = formatAge(p.updated_at || p.timestamp);
            if (t.agent === 'atlas') {
                const sg = p.spend_gate || {};
                const cap = p.approved_ad_spend_monthly_cap_cad ?? 0;
                const liquid = p.liquid_cad ?? 0;
                out.push(`  ${t.label}: gate=${sg.status || '?'} | cap=$${cap}/mo | liquid=$${Number(liquid).toLocaleString()} | ${age}`);
            } else if (t.agent === 'bravo') {
                const rev = p.revenue || {};
                const mrr = rev.net_mrr_usd ?? p.mrr_usd ?? 0;
                const conc = rev.bennett_concentration_pct ?? '?';
                out.push(`  ${t.label}: MRR=$${mrr} USD | conc=${conc}% | ${age}`);
            } else {
                const req = p.spend_request_cad ?? 0;
                const cp = p.content_pipeline || {};
                const drafts = cp.drafts_in_review ?? cp.in_review ?? '?';
                out.push(`  ${t.label}: spend_request=$${req} CAD | drafts_in_review=${drafts} | ${age}`);
            }
        }
        return bot.sendMessage(chatId, out.join('\n'));
    }

    // /sibling <agent> [file] — read a sibling agent's brain/*.md.
    // Atlas-V3.2 parity: bare agent → list brain/, agent+file → first 3000 chars.
    if (text.startsWith('/sibling')) {
        const args = text.slice('/sibling'.length).trim().split(/\s+/).filter(Boolean);
        if (!args.length) {
            return bot.sendMessage(chatId, [
                'Usage: /sibling <bravo|atlas|aura> [filename]',
                'Examples:',
                '  /sibling bravo            (list Bravo\'s brain/)',
                '  /sibling bravo SOUL       (read Bravo\'s brain/SOUL.md)',
                '  /sibling atlas CFO_GATE_CONTRACT',
            ].join('\n'));
        }
        const agent = args[0].toLowerCase();
        if (!SIBLING_REPOS[agent]) {
            return bot.sendMessage(chatId, `Unknown agent '${agent}'. Try: ${Object.keys(SIBLING_REPOS).filter(a => a !== 'maven').join(', ')}`);
        }
        const repo = SIBLING_REPOS[agent];
        if (!fs.existsSync(repo)) {
            return bot.sendMessage(chatId, `${agent} repo not on this machine: ${repo}`);
        }
        const brainDir = path.join(repo, 'brain');
        if (!fs.existsSync(brainDir)) {
            return bot.sendMessage(chatId, `${agent} has no brain/ dir at ${brainDir}`);
        }
        if (args.length === 1) {
            const names = fs.readdirSync(brainDir).filter(n => n.endsWith('.md')).sort();
            return bot.sendMessage(chatId, `${agent}/brain/ contents:\n  ${names.join('\n  ')}`.substring(0, 3500));
        }
        let name = args.slice(1).join(' ').replace(/[\\/]/g, '');
        if (!name.endsWith('.md')) name += '.md';
        const file = path.join(brainDir, name);
        if (!fs.existsSync(file)) {
            const names = fs.readdirSync(brainDir).filter(n => n.endsWith('.md')).sort();
            return bot.sendMessage(chatId, `${agent}/brain/${name} not found.\nAvailable: ${names.join(', ')}`.substring(0, 3500));
        }
        let body = fs.readFileSync(file, 'utf8');
        if (body.length > 3000) body = body.slice(0, 3000) + `\n\n... (${body.length - 3000} more chars)`;
        return bot.sendMessage(chatId, `=== ${agent}/brain/${name} ===\n${body}`);
    }

    if (text === '/spend') {
        const cfoCheck = readCfoPulse();
        if (!cfoCheck.ok) {
            return bot.sendMessage(chatId, `CFO pulse: ${cfoCheck.reason}`);
        }
        const sg = cfoCheck.pulse.spend_gate || {};
        const lines = [
            `Atlas spend gate: ${sg.status}`,
            `Pulse age: ${cfoCheck.ageHours.toFixed(1)}h`,
            '',
            'Approvals:',
        ];
        for (const channel of Object.keys(sg.approvals || {})) {
            for (const brand of Object.keys(sg.approvals[channel] || {})) {
                const cap = sg.approvals[channel][brand];
                const usd = (cap && cap.daily_budget_usd != null) ? `$${cap.daily_budget_usd}/d` : 'n/a';
                lines.push(`  ${channel} / ${brand} → ${usd}`);
            }
        }
        return bot.sendMessage(chatId, lines.join('\n'));
    }

    if (text === '/campaigns') {
        return new Promise((resolve) => {
            execFile(PYTHON, ['scripts/send_gateway.py', '--json', 'stats'],
                { cwd: __dirname, windowsHide: true, timeout: 15000 },
                (err, out, errOut) => {
                    bot.sendMessage(chatId, (out || errOut || err?.message || 'no result').substring(0, 3500))
                        .then(resolve).catch(() => resolve());
                });
        });
    }

    if (text === '/killswitch') {
        process.env.MAVEN_FORCE_DRY_RUN = '1';
        log('[KILLSWITCH] Engaged via Telegram.');
        return bot.sendMessage(chatId,
            '🔒 MAVEN_FORCE_DRY_RUN=1 set in this bridge process. All sends will short-circuit at send_gateway. Persist by editing .env.agents and `pm2 restart maven-telegram`.');
    }

    if (text === '/unleash') {
        delete process.env.MAVEN_FORCE_DRY_RUN;
        log('[KILLSWITCH] Disengaged via Telegram.');
        return bot.sendMessage(chatId, 'Killswitch off in this process. Edit .env.agents to make persistent.');
    }

    if (text === '/pulse') {
        return new Promise((resolve) => {
            execFile(PYTHON, ['scripts/state_sync.py', '--note', 'pulse refresh from telegram'],
                { cwd: __dirname, windowsHide: true, timeout: 12000 },
                (err, out, errOut) => {
                    bot.sendMessage(chatId, (out || errOut || err?.message || 'done').substring(0, 1500))
                        .then(resolve).catch(() => resolve());
                });
        });
    }

    if (text === '/sync') {
        return new Promise((resolve) => {
            execFile(PYTHON, ['scripts/state_sync.py', '--note', 'session sync from telegram', '--mem0'],
                { cwd: __dirname, windowsHide: true, timeout: 30000 },
                (err, out, errOut) => {
                    bot.sendMessage(chatId, (out || errOut || err?.message || 'done').substring(0, 1500))
                        .then(resolve).catch(() => resolve());
                });
        });
    }

    if (text === '/audit') {
        return new Promise((resolve) => {
            execFile(PYTHON, ['scripts/self_audit.py', '--json'],
                { cwd: __dirname, windowsHide: true, timeout: 30000 },
                (err, out, errOut) => {
                    let summary = (out || errOut || err?.message || '').substring(0, 3500);
                    try {
                        const idx = (out || '').indexOf('{');
                        if (idx >= 0) {
                            const j = JSON.parse(out.slice(idx));
                            summary = `health: ${j.health_score}/100 | agents ${j.agents_total - j.agents_missing_frontmatter.length}/${j.agents_total} | skills ${j.skills_total - j.skills_missing_frontmatter.length}/${j.skills_total} | send_gateway ${j.send_gateway_tests_pass} | pulse_fresh ${j.cmo_pulse_fresh}`;
                        }
                    } catch (_) {}
                    bot.sendMessage(chatId, summary).then(resolve).catch(() => resolve());
                });
        });
    }

    if (text === '/tests') {
        const files = [
            'scripts/test_send_gateway.py',
            'scripts/test_late_publisher.py',
            'scripts/test_instagram_engine.py',
            'scripts/test_content_pipeline.py',
            'scripts/test_performance_reporter.py',
            'scripts/test_notify.py',
            'scripts/test_script_ideation.py',
            'scripts/test_c_suite_context.js',
        ];
        const lines = ['Maven test sweep:'];
        for (const f of files) {
            const isJs = f.endsWith('.js');
            const cmd = isJs ? NODE_EXE : PYTHON;
            const r = await new Promise((resolve) => {
                execFile(cmd, [f], { cwd: __dirname, windowsHide: true, timeout: 60000 },
                    (err, out, errOut) => resolve({ code: err ? (err.code || 1) : 0, out, err: errOut }));
            });
            const tail = ((r.out || '') + (r.err || '')).split('\n').reverse().find(l => /Ran \d+ tests|tests? passed|✓|FAIL/i.test(l)) || '(no result)';
            lines.push(`  ${f.replace('scripts/test_', '').replace(/\.(py|js)$/, '')}: ${tail.trim()} ${r.code === 0 ? 'OK' : 'FAIL'}`);
        }
        return bot.sendMessage(chatId, lines.join('\n'));
    }

    if (text === '/inbox') {
        return new Promise((resolve) => {
            execFile(PYTHON, ['scripts/agent_inbox.py', 'list', '--to', 'maven'],
                { cwd: __dirname, windowsHide: true, timeout: 15000 },
                (err, out, errOut) => {
                    bot.sendMessage(chatId, ((out || errOut || '(no unread)').substring(0, 3500)))
                        .then(resolve).catch(() => resolve());
                });
        });
    }

    const postMatch = text.match(/^\/post\s+(\S+)\s+(.+)/);
    if (postMatch) {
        const to = postMatch[1].toLowerCase();
        const body = postMatch[2];
        if (!['bravo', 'atlas', 'aura'].includes(to)) {
            return bot.sendMessage(chatId, `unknown target '${to}'. Use bravo|atlas|aura.`);
        }
        const sep = body.indexOf('||');
        if (sep < 0) {
            return bot.sendMessage(chatId, 'format: /post bravo subject || body');
        }
        const subject = body.slice(0, sep).trim();
        const messageBody = body.slice(sep + 2).trim();
        return new Promise((resolve) => {
            execFile(PYTHON, [
                'scripts/agent_inbox.py', '--json', 'post',
                '--from', 'maven', '--to', to,
                '--subject', subject, '--body', messageBody,
                '--priority', 'normal',
            ], { cwd: __dirname, windowsHide: true, timeout: 10000 },
                (err, out, errOut) => {
                    bot.sendMessage(chatId, (out || errOut || err?.message || '').substring(0, 1500))
                        .then(resolve).catch(() => resolve());
                });
        });
    }

    // ---- HARD CFO GATE: paid-launch interception ----
    if (PAID_LAUNCH_PATTERN.test(text) && classifyTier(text) <= 1) {
        addToHistory(chatId, 'user', text);
        await handlePaidLaunch(chatId, text);
        return;
    }

    // ---- KILLSWITCH ENFORCEMENT ----
    if (KILLSWITCH_ENGAGED() && PAID_LAUNCH_PATTERN.test(text)) {
        return bot.sendMessage(chatId,
            '🔒 MAVEN_FORCE_DRY_RUN engaged — paid launches are blocked at the bridge level. Use /unleash or edit .env.agents.');
    }

    // ---- DEFAULT: spawn Claude ----
    try {
        let modelOverride = null;
        let workingText = text;
        const modelMatch = workingText.match(/^!(opus|sonnet|haiku)\s+/i);
        if (modelMatch) {
            modelOverride = modelMatch[1].toLowerCase();
            workingText = workingText.replace(/^!(opus|sonnet|haiku)\s+/i, '');
        }

        addToHistory(chatId, 'user', workingText);
        await bot.sendChatAction(chatId, 'typing');
        // Brand as Maven, not Claude — user is talking to Maven; underlying
        // model is an implementation detail. Parity with Bravo + Atlas bridges.
        await bot.sendMessage(chatId, modelOverride ? `Maven (${modelOverride}) thinking...` : 'Maven thinking...');

        const result = await executeClaude(workingText, chatId, modelOverride);

        // Approval-gate detection
        const confirmMatch = (result || '').match(CONFIRM_PATTERN);
        if (confirmMatch) {
            const description = confirmMatch[1].trim();
            PENDING_CONFIRMATIONS[String(chatId)] = { description, timestamp: Date.now() };
            const idx = result.indexOf(confirmMatch[0]);
            const beforeConfirm = result.substring(0, idx).trim();
            if (beforeConfirm) {
                addToHistory(chatId, 'assistant', beforeConfirm);
                const preChunks = beforeConfirm.match(/[\s\S]{1,4000}/g) || [];
                for (const c of preChunks) await bot.sendMessage(chatId, c);
            }
            await bot.sendMessage(chatId,
                `🔒 Maven wants to perform a destructive action:\n\n${description}\n\nApprove?`,
                {
                    reply_markup: {
                        inline_keyboard: [[
                            { text: '✅ Yes, proceed', callback_data: 'approve_yes' },
                            { text: '❌ No, cancel', callback_data: 'approve_no' },
                        ]],
                    },
                });
            return;
        }

        addToHistory(chatId, 'assistant', result || 'No response.');
        const chunks = (result || 'No response.').match(/[\s\S]{1,4000}/g) || ['No response.'];
        for (const c of chunks) await bot.sendMessage(chatId, c);
        log(`[SENT] Delivered ${chunks.length} chunk(s) to chat ${chatId}`);
    } catch (err) {
        log(`[CRASH] ${err.message}\n${err.stack}`);
        bot.sendMessage(chatId, `Error: ${err.message}`).catch(() => {});
    }
});

// ---- CALLBACK QUERY (inline buttons) ----
bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const callbackUserId = String(query.from.id);
    const data = query.data;

    if (!ALLOWED_USERS.includes(callbackUserId)) {
        log(`[BLOCKED] Unauthorized callback from ${callbackUserId}`);
        return bot.answerCallbackQuery(query.id, { text: 'Unauthorized' }).catch(() => {});
    }

    await bot.answerCallbackQuery(query.id).catch(() => {});

    // Paid-launch gate
    if (data === 'paid_yes' || data === 'paid_no') {
        const pending = PENDING_PAID[String(chatId)];
        if (!pending) {
            return bot.sendMessage(chatId, 'No pending paid-launch confirmation.');
        }
        delete PENDING_PAID[String(chatId)];

        if (data === 'paid_no') {
            log(`[CFO GATE] User cancelled paid launch: ${pending.description}`);
            await bot.sendMessage(chatId, '❌ Paid launch cancelled. Logging to inbox.');
            execFile(PYTHON, [
                'scripts/agent_inbox.py', 'post',
                '--from', 'maven', '--to', 'bravo',
                '--priority', 'low',
                '--subject', 'Paid launch cancelled by CC via Telegram',
                '--body', `CC cancelled the following paid-launch request: ${pending.description}`,
            ], { cwd: __dirname, windowsHide: true, timeout: 10000 }, () => {});
            return;
        }

        // ✅ Launch
        log(`[CFO GATE] User approved paid launch: ${pending.description}`);
        await bot.sendMessage(chatId, '✅ Approved. Launching via Claude with CFO-gate-cleared context...');
        // Notify Bravo + Atlas in parallel
        for (const to of ['bravo', 'atlas']) {
            execFile(PYTHON, [
                'scripts/agent_inbox.py', 'post',
                '--from', 'maven', '--to', to,
                '--priority', 'normal',
                '--subject', 'Maven launching paid campaign — approved by CC',
                '--body', `Approved via Maven Telegram bridge. Request: ${pending.description}`,
            ], { cwd: __dirname, windowsHide: true, timeout: 10000 }, () => {});
        }
        const followUp = `CC has APPROVED this paid-launch request after the CFO spend gate passed: "${pending.description}". Execute the launch now via the appropriate engine (meta_ads_engine or google_ads_engine), routing through send_gateway.`;
        const result = await executeClaude(followUp, chatId);
        addToHistory(chatId, 'assistant', result || 'Done.');
        const chunks = (result || 'Done.').match(/[\s\S]{1,4000}/g) || ['Done.'];
        for (const c of chunks) await bot.sendMessage(chatId, c);
        return;
    }

    // Generic destructive-action gate
    const pending = PENDING_CONFIRMATIONS[String(chatId)];
    if (!pending) {
        return bot.sendMessage(chatId, 'No pending confirmation.');
    }
    delete PENDING_CONFIRMATIONS[String(chatId)];

    if (data === 'approve_yes') {
        await bot.sendMessage(chatId, '✅ Approved. Executing...');
        addToHistory(chatId, 'user', `APPROVED: ${pending.description}`);
        const followUp = `The user has APPROVED: "${pending.description}". Proceed.`;
        const result = await executeClaude(followUp, chatId);
        addToHistory(chatId, 'assistant', result || 'Done.');
        const chunks = (result || 'Done.').match(/[\s\S]{1,4000}/g) || ['Done.'];
        for (const c of chunks) await bot.sendMessage(chatId, c);
    } else {
        await bot.sendMessage(chatId, '❌ Cancelled.');
        addToHistory(chatId, 'assistant', `Cancelled: ${pending.description}`);
    }
});

// ---- SHUTDOWN ----
let shuttingDown = false;
const shutdown = async (sig) => {
    if (shuttingDown) return;
    shuttingDown = true;
    log(`[SHUTDOWN] ${sig} — stopping polling...`);
    for (const c of activeChildren) killTree(c.pid);
    try { await bot.stopPolling(); } catch (_) {}
    setTimeout(() => process.exit(0), 2000);
};
process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));

// ---- POLLING ERROR HANDLING ----
let pollErrorCount = 0;
let pollingDormant = false;
bot.on('polling_error', (e) => {
    pollErrorCount++;
    const msg = e.message || String(e);
    // 409 Conflict — another bridge owns this token. Same fix as Bravo:
    // stop polling, wait 30s for the conflicting process to release the token,
    // then exit non-zero so PM2 autorestarts. Old "dormant until restart"
    // behavior left bridges silently broken for days because PM2 saw "online".
    if (msg.includes('409') || msg.includes('Conflict')) {
        if (!pollingDormant) {
            pollingDormant = true;
            log('[POLL] 409 conflict: another Maven bridge owns this token. ' +
                'Stopping polling and exiting in 30s so PM2 can restart cleanly.');
        }
        bot.stopPolling().catch(() => {});
        setTimeout(() => {
            log('[POLL] 30s elapsed after 409, exiting with code 1 to trigger PM2 restart.');
            process.exit(1);
        }, 30000);
        return;
    }
    if (msg.includes('401')) {
        log('[POLL] 401 — MAVEN_TELEGRAM_BOT_TOKEN invalid or revoked. Exiting.');
        process.exit(1);
        return;
    }
    if (pollErrorCount === 1 || pollErrorCount % 50 === 0) {
        log(`[POLL] Error: ${msg} (count: ${pollErrorCount})`);
    }
});

process.on('unhandledRejection', (err) => {
    log(`[UNHANDLED] ${err.message || err}`);
});

log(`Maven Bridge V1.0 ready. Platform: ${IS_MAC ? 'macOS' : 'Windows'}. Killswitch: ${KILLSWITCH_ENGAGED() ? 'ENGAGED' : 'OFF'}.`);

// ---- START POLLING ----
try {
    const ps = bot.startPolling();
    log('[POLL] Polling requested.');
    if (ps && typeof ps.catch === 'function') ps.catch((err) => log(`[POLL] Failed to start: ${err.message}`));
} catch (err) {
    log(`[POLL] Failed to start: ${err.message}`);
}

// ---- STARTUP HEALTH CHECK ----
// Telegram getMe (must return 200) + Anthropic API key (must return 200 from
// a tiny ping). Fails fast on 401 with a clear log + Telegram alert.
setTimeout(() => {
    const https = require('https');

    // 1. Telegram getMe
    https.get(`https://api.telegram.org/bot${TELEGRAM_TOKEN}/getMe`, (res) => {
        let body = '';
        res.on('data', d => body += d.toString());
        res.on('end', () => {
            if (res.statusCode === 200) {
                try {
                    const j = JSON.parse(body);
                    log(`[HEALTH] Telegram getMe: OK (bot @${j.result?.username || '?'} id=${j.result?.id || '?'})`);
                } catch (_) { log('[HEALTH] Telegram getMe: OK (parse fail)'); }
            } else {
                log(`[HEALTH] Telegram getMe FAILED HTTP ${res.statusCode} — check MAVEN_TELEGRAM_BOT_TOKEN`);
                if (ALLOWED_USERS.length > 0) {
                    bot.sendMessage(ALLOWED_USERS[0],
                        `⚠️ Maven startup: Telegram auth failed (HTTP ${res.statusCode}). Check MAVEN_TELEGRAM_BOT_TOKEN in .env.agents, then: pm2 restart maven-telegram`)
                        .catch(() => {});
                }
            }
        });
    }).on('error', (e) => log(`[HEALTH] Telegram check error: ${e.message}`));

    // 2. Anthropic ping
    const apiKey = process.env.ANTHROPIC_API_KEY;
    if (!apiKey) {
        log('[HEALTH] ANTHROPIC_API_KEY missing — Claude will fail');
        return;
    }
    const body = JSON.stringify({
        model: 'claude-haiku-4-5-20251001',
        max_tokens: 5,
        messages: [{ role: 'user', content: 'ping' }],
    });
    const req = https.request({
        hostname: 'api.anthropic.com',
        path: '/v1/messages',
        method: 'POST',
        headers: {
            'x-api-key': apiKey,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
            'content-length': Buffer.byteLength(body),
        },
    }, (res) => {
        if (res.statusCode === 200) {
            log('[HEALTH] Anthropic API: OK');
        } else {
            log(`[HEALTH] Anthropic API FAILED HTTP ${res.statusCode}`);
            if (ALLOWED_USERS.length > 0) {
                bot.sendMessage(ALLOWED_USERS[0],
                    `⚠️ Maven startup: Anthropic API check failed (HTTP ${res.statusCode}). Update ANTHROPIC_API_KEY then: pm2 restart maven-telegram`)
                    .catch(() => {});
            }
        }
    });
    req.on('error', (e) => log(`[HEALTH] Anthropic check error: ${e.message}`));
    req.write(body);
    req.end();
}, 5000);
