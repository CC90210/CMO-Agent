// PM2 ecosystem for Maven (CMO Agent)
//
// Distinct from Bravo's ecosystem (Business-Empire-Agent) and Atlas's
// (CFO-Agent). All three can run on the same machine — each polls a
// different Telegram bot token, so no conflict.
//
// Usage:
//   pm2 start ecosystem.config.js
//   pm2 save                       # persist across reboots
//   pm2 status                     # confirm maven-telegram online
//   pm2 logs maven-telegram        # tail bridge logs
//   pm2 restart maven-telegram     # restart after .env.agents change

module.exports = {
    apps: [
        {
            name: 'maven-telegram',
            script: 'telegram_agent.js',
            cwd: process.platform === 'win32'
                ? 'C:/Users/User/CMO-Agent'
                : (process.env.MAVEN_REPO || `${process.env.HOME || ''}/CMO-Agent`),
            autorestart: true,
            max_restarts: 10,
            min_uptime: 10000,
            restart_delay: 4000,
            max_memory_restart: '512M',
            kill_timeout: 5000,
            env: {
                NODE_ENV: 'production',
            },
            // Logs land alongside Bravo's PM2 logs but namespaced to maven-*
            out_file: 'tmp/pm2-maven-telegram-out.log',
            error_file: 'tmp/pm2-maven-telegram-error.log',
            merge_logs: true,
            time: true,
        },
    ],
};
