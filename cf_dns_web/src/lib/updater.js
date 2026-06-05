const fs = require('fs');
const path = require('path');
const https = require('https');
const http = require('http');

const DATA_DIR = path.join(process.cwd(), 'data');
const CONFIG_FILE = path.join(DATA_DIR, 'configs.json');
const SETTINGS_FILE = path.join(DATA_DIR, 'settings.json');

if (!fs.existsSync(DATA_DIR)) {
  fs.mkdirSync(DATA_DIR, { recursive: true });
}
if (!fs.existsSync(CONFIG_FILE)) {
  fs.writeFileSync(CONFIG_FILE, '[]');
}
if (!fs.existsSync(SETTINGS_FILE)) {
  fs.writeFileSync(SETTINGS_FILE, JSON.stringify({ interval: 30 }));
}

function fetchPublicIp() {
  return new Promise((resolve, reject) => {
    http.get('http://ipv4.icanhazip.com', (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => resolve(data.trim()));
    }).on('error', reject);
  });
}

function fetchCloudflare(url, options, data = null) {
  return new Promise((resolve, reject) => {
    const req = https.request(url, options, (res) => {
      let body = '';
      res.on('data', chunk => body += chunk);
      res.on('end', () => {
        try {
          resolve(JSON.parse(body));
        } catch (e) {
          reject(e);
        }
      });
    });
    req.on('error', reject);
    if (data) req.write(data);
    req.end();
  });
}

async function checkAndUpdateDns(force = false) {
  let results = [];
  try {
    const configsStr = fs.readFileSync(CONFIG_FILE, 'utf8');
    const configs = configsStr ? JSON.parse(configsStr) : [];
    if (!configs.length) return ["Chưa có cấu hình nào."];

    const currentIp = await fetchPublicIp();
    if (!currentIp) return ["Không lấy được IP Public hiện tại."];

    for (const conf of configs) {
      const { AUTH_EMAIL, AUTH_KEY, ZONE_ID, RECORD_NAME, PROXIED } = conf;
      if (!AUTH_EMAIL || !AUTH_KEY || !ZONE_ID || !RECORD_NAME) {
        results.push(`[${RECORD_NAME}] Bỏ qua vì thiếu thông tin.`);
        continue;
      }

      try {
        const getOptions = {
          method: 'GET',
          headers: {
            'X-Auth-Email': AUTH_EMAIL,
            'Authorization': `Bearer ${AUTH_KEY}`,
            'Content-Type': 'application/json'
          }
        };
        const resData = await fetchCloudflare(`https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records?type=A&name=${RECORD_NAME}`, getOptions);
        
        if (!resData.success) {
          results.push(`[${RECORD_NAME}] API Error: ${resData.errors?.[0]?.message}`);
          continue;
        }

        const records = resData.result;
        if (!records || records.length === 0) {
          results.push(`[${RECORD_NAME}] Không tìm thấy DNS record.`);
          continue;
        }

        const cfIp = records[0].content;
        const recordId = records[0].id;

        if (currentIp === cfIp && !force) {
          continue; 
        }

        const isProxied = PROXIED === 'true' || PROXIED === true;
        const updateData = JSON.stringify({
          type: "A",
          name: RECORD_NAME,
          content: currentIp,
          ttl: 120,
          proxied: isProxied
        });

        const putOptions = {
          method: 'PUT',
          headers: {
            'X-Auth-Email': AUTH_EMAIL,
            'Authorization': `Bearer ${AUTH_KEY}`,
            'Content-Type': 'application/json',
            'Content-Length': Buffer.byteLength(updateData)
          }
        };

        const updateRes = await fetchCloudflare(`https://api.cloudflare.com/client/v4/zones/${ZONE_ID}/dns_records/${recordId}`, putOptions, updateData);
        if (updateRes.success) {
          const msg = `[${RECORD_NAME}] Cập nhật thành công IP: ${currentIp}`;
          console.log(msg);
          results.push(msg);
        } else {
          const msg = `[${RECORD_NAME}] Lỗi cập nhật: ${updateRes.errors?.[0]?.message}`;
          console.error(msg);
          results.push(msg);
        }
      } catch (err) {
        results.push(`[${RECORD_NAME}] Error: ${err.message}`);
      }
    }
  } catch (err) {
    results.push(`Lỗi hệ thống: ${err.message}`);
  }
  return results;
}

function getSettings() {
  try {
    const s = fs.readFileSync(SETTINGS_FILE, 'utf8');
    return JSON.parse(s);
  } catch {
    return { interval: 30 };
  }
}

function getConfigs() {
  try {
    const s = fs.readFileSync(CONFIG_FILE, 'utf8');
    return JSON.parse(s);
  } catch {
    return [];
  }
}

function saveConfigs(data) {
  fs.writeFileSync(CONFIG_FILE, JSON.stringify(data, null, 2));
}

function saveSettings(data) {
  fs.writeFileSync(SETTINGS_FILE, JSON.stringify(data, null, 2));
}

async function fetchRecords(email, key, zoneId) {
  if (!email || !key || !zoneId) throw new Error("Missing credentials");
  
  const getOptions = {
    method: 'GET',
    headers: {
      'X-Auth-Email': email,
      'Authorization': `Bearer ${key}`,
      'Content-Type': 'application/json'
    }
  };
  const resData = await fetchCloudflare(`https://api.cloudflare.com/client/v4/zones/${zoneId}/dns_records?type=A`, getOptions);
  if (!resData.success) {
    throw new Error(resData.errors?.[0]?.message || 'Unknown API Error');
  }
  return resData.result;
}

module.exports = {
  checkAndUpdateDns,
  getSettings,
  saveSettings,
  getConfigs,
  saveConfigs,
  fetchRecords
};
