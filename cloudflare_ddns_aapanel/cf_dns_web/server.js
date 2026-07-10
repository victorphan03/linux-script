const { createServer } = require('http')
const { parse } = require('url')
const next = require('next')
const { checkAndUpdateDns, getSettings } = require('./src/lib/updater')

const dev = process.env.NODE_ENV !== 'production'
const hostname = 'localhost'
const port = process.env.PORT || 3000
const app = next({ dev, hostname, port })
const handle = app.getRequestHandler()

async function startDaemon() {
  console.log("Starting CF DNS Daemon loop...");
  while (true) {
    try {
      await checkAndUpdateDns(false);
    } catch(e) {
      console.error(e);
    }
    
    let interval = 30;
    try {
      const settings = getSettings();
      interval = Math.max(10, parseInt(settings.interval) || 30);
    } catch (e) {}

    await new Promise(r => setTimeout(r, interval * 1000));
  }
}

app.prepare().then(() => {
  createServer(async (req, res) => {
    try {
      const parsedUrl = parse(req.url, true)
      await handle(req, res, parsedUrl)
    } catch (err) {
      console.error('Error occurred handling', req.url, err)
      res.statusCode = 500
      res.end('internal server error')
    }
  })
    .once('error', (err) => {
      console.error(err)
      process.exit(1)
    })
    .listen(port, () => {
      console.log(`> Ready on http://${hostname}:${port}`)
      startDaemon();
    })
})
