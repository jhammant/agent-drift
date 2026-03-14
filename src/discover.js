#!/usr/bin/env node
/**
 * Agent Drift — Discovery Engine
 * Finds AI chatbots in the wild using search engines and Shodan.
 * 
 * Usage:
 *   drift-discover --industry "insurance"
 *   drift-discover --industry "banking" --region UK --limit 50
 *   drift-discover --shodan "intercom" --limit 20
 *   drift-discover --dork 'intext:"powered by intercom"'
 *   drift-discover --company "chipotle" 
 *   drift-discover --list fortune500.txt --output targets.json
 */

import { readFileSync, writeFileSync } from 'fs';

// Google dork templates for finding AI chatbots
const DORK_TEMPLATES = {
  // Widget-specific dorks
  intercom: [
    'intext:"powered by Intercom"',
    'intext:"We run on Intercom"',
    'site:*.intercom.help',
  ],
  drift: [
    'intext:"powered by Drift"',
    'inurl:drift.com/messaging',
  ],
  zendesk: [
    'intext:"powered by Zendesk"',
    'inurl:zendesk.com/embeddable',
  ],
  tidio: [
    'intext:"powered by Tidio"',
    'inurl:tidio.co',
  ],
  generic_ai: [
    'intext:"AI assistant" intext:"chat with"',
    'intext:"virtual assistant" intext:"how can I help"',
    'intext:"powered by ChatGPT"',
    'intext:"powered by OpenAI"',
    'intext:"AI-powered support"',
    'intext:"AI customer service"',
  ],

  // Industry-specific
  insurance: [
    '"insurance" "chat with us" "AI"',
    '"insurance" "virtual assistant"',
    '"get a quote" "chat" "AI assistant"',
  ],
  banking: [
    '"banking" "virtual assistant" "chat"',
    '"bank" "AI assistant" "help"',
    '"financial services" "chatbot"',
  ],
  healthcare: [
    '"healthcare" "virtual assistant"',
    '"patient portal" "chat"',
    '"health" "AI assistant"',
  ],
  ecommerce: [
    '"shop" "chat with us" "AI"',
    '"customer support" "chatbot" "order"',
    '"store" "virtual assistant" "help"',
  ],
  saas: [
    '"SaaS" "chat with us"',
    '"software" "AI support"',
    '"platform" "virtual assistant"',
  ],
  travel: [
    '"travel" "AI assistant" "book"',
    '"airline" "virtual assistant"',
    '"hotel" "chatbot" "reservation"',
  ],
  telecom: [
    '"telecom" "virtual assistant"',
    '"mobile" "AI support" "chat"',
    '"broadband" "chatbot"',
  ],
};

// Shodan search queries for exposed chatbot infrastructure
const SHODAN_QUERIES = {
  intercom: 'http.html:"intercom" http.html:"chat"',
  drift: 'http.html:"drift" http.html:"chat-widget"',
  zendesk: 'http.html:"zendesk" http.html:"web_widget"',
  chatbot_api: 'http.title:"chatbot" port:443',
  openai_api: '"openai" "api" port:443 http.status:200',
  custom_chat: 'http.html:"chat-container" http.html:"ai-assistant"',
};

// Brave Search API integration
async function braveSearch(query, count = 10) {
  const apiKey = process.env.BRAVE_API_KEY;
  if (!apiKey) {
    console.log('   ⚠️  BRAVE_API_KEY not set — using simulated results');
    return [];
  }

  try {
    const params = new URLSearchParams({ q: query, count: String(count) });
    const res = await fetch(`https://api.search.brave.com/res/v1/web/search?${params}`, {
      headers: { 'X-Subscription-Token': apiKey, 'Accept': 'application/json' },
    });

    if (!res.ok) {
      if (res.status === 429) {
        console.log('   ⚠️  Rate limited — waiting 2s...');
        await new Promise(r => setTimeout(r, 2000));
        return braveSearch(query, count);
      }
      return [];
    }

    const data = await res.json();
    return (data.web?.results || []).map(r => ({
      url: r.url,
      title: r.title,
      description: r.description,
      domain: new URL(r.url).hostname,
    }));
  } catch (e) {
    console.log(`   ❌ Search error: ${e.message}`);
    return [];
  }
}

// Shodan integration
async function shodanSearch(query, limit = 20) {
  const apiKey = process.env.SHODAN_API_KEY;
  if (!apiKey) {
    console.log('   ⚠️  SHODAN_API_KEY not set — skipping Shodan');
    return [];
  }

  try {
    const params = new URLSearchParams({ key: apiKey, query, minify: 'true' });
    const res = await fetch(`https://api.shodan.io/shodan/host/search?${params}`);
    
    if (!res.ok) return [];
    
    const data = await res.json();
    return (data.matches || []).slice(0, limit).map(m => ({
      ip: m.ip_str,
      port: m.port,
      org: m.org,
      hostname: m.hostnames?.[0],
      url: `https://${m.hostnames?.[0] || m.ip_str}:${m.port}`,
    }));
  } catch (e) {
    return [];
  }
}

// Widget detection on fetched pages
const WIDGET_PATTERNS = [
  { name: 'Intercom', regex: /intercom|widget\.intercom\.io/i },
  { name: 'Drift', regex: /drift\.com|js\.driftt\.com|drift-widget/i },
  { name: 'Zendesk', regex: /zendesk|zdassets\.com|web_widget/i },
  { name: 'Tidio', regex: /tidio|tidiochat/i },
  { name: 'Crisp', regex: /crisp\.chat|crisp-client/i },
  { name: 'HubSpot', regex: /hubspot.*messages|hs-scripts.*chat/i },
  { name: 'Freshdesk', regex: /freshdesk|freshchat|freshworks.*widget/i },
  { name: 'LiveChat', regex: /livechat|livechatinc/i },
  { name: 'Ada', regex: /ada\.cx|ada-chat/i },
  { name: 'ChatGPT Widget', regex: /chatgpt.*widget|openai.*chat/i },
  { name: 'Custom AI', regex: /ai.assistant|virtual.assistant|chatbot/i },
];

async function checkUrl(url) {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    const res = await fetch(url, {
      signal: controller.signal,
      headers: { 'User-Agent': 'Mozilla/5.0 (compatible; AgentDrift/1.0)' },
      redirect: 'follow',
    });
    clearTimeout(timeout);
    if (!res.ok) return null;
    const html = await res.text();
    
    const found = [];
    for (const p of WIDGET_PATTERNS) {
      if (p.regex.test(html)) {
        found.push(p.name);
      }
    }
    return found.length > 0 ? found : null;
  } catch {
    return null;
  }
}

// Main discovery pipeline
async function discover(options) {
  const { industry, company, dork, shodan, list, limit = 30, region } = options;
  const targets = new Map(); // domain -> { url, widgets, source }
  
  console.log('🔍 Agent Drift — Discovery Engine\n');
  
  // Step 1: Build search queries
  const queries = [];
  
  if (dork) {
    queries.push({ query: dork, source: 'custom dork' });
  }
  
  if (company) {
    queries.push(
      { query: `"${company}" "chat with us"`, source: `company:${company}` },
      { query: `"${company}" "virtual assistant"`, source: `company:${company}` },
      { query: `site:${company}.com "chat"`, source: `company:${company}` },
    );
  }
  
  if (industry && DORK_TEMPLATES[industry]) {
    for (const q of DORK_TEMPLATES[industry]) {
      const regionQ = region ? `${q} "${region}"` : q;
      queries.push({ query: regionQ, source: `industry:${industry}` });
    }
  }
  
  // Always include generic AI chatbot dorks
  if (!dork && !list) {
    for (const q of DORK_TEMPLATES.generic_ai.slice(0, 3)) {
      queries.push({ query: q, source: 'generic' });
    }
  }
  
  // Step 2: Search
  if (queries.length > 0) {
    console.log(`📡 Running ${queries.length} search queries...\n`);
    
    for (const { query, source } of queries) {
      console.log(`   🔎 "${query.substring(0, 50)}..."`);
      const results = await braveSearch(query, Math.min(10, limit));
      
      for (const r of results) {
        if (!targets.has(r.domain)) {
          targets.set(r.domain, {
            url: r.url,
            title: r.title,
            domain: r.domain,
            source,
            widgets: null,
          });
        }
      }
      
      await new Promise(r => setTimeout(r, 1100)); // rate limit: 1 req/sec
    }
  }
  
  // Step 3: Load from file
  if (list) {
    const urls = readFileSync(list, 'utf-8').split('\n').filter(Boolean);
    for (const url of urls) {
      try {
        const domain = new URL(url.startsWith('http') ? url : `https://${url}`).hostname;
        targets.set(domain, {
          url: url.startsWith('http') ? url : `https://${url}`,
          domain,
          source: 'list',
          widgets: null,
        });
      } catch {}
    }
  }
  
  // Step 4: Shodan
  if (shodan) {
    const shodanQuery = SHODAN_QUERIES[shodan] || shodan;
    console.log(`\n🔍 Shodan: "${shodanQuery}"`);
    const shodanResults = await shodanSearch(shodanQuery, limit);
    for (const r of shodanResults) {
      if (r.hostname && !targets.has(r.hostname)) {
        targets.set(r.hostname, {
          url: r.url,
          domain: r.hostname,
          source: 'shodan',
          org: r.org,
          widgets: null,
        });
      }
    }
  }
  
  console.log(`\n📋 Found ${targets.size} unique domains to check\n`);
  
  // Step 5: Check each target for widgets
  console.log('🕷️  Checking for AI chatbot widgets...\n');
  
  let checked = 0;
  let withWidgets = 0;
  
  for (const [domain, target] of targets) {
    if (checked >= limit) break;
    checked++;
    
    process.stdout.write(`   [${checked}/${Math.min(targets.size, limit)}] ${domain}...`);
    
    const widgets = await checkUrl(target.url);
    target.widgets = widgets;
    
    if (widgets) {
      withWidgets++;
      console.log(` ✅ ${widgets.join(', ')}`);
    } else {
      console.log(' —');
    }
  }
  
  // Step 6: Report
  const results = Array.from(targets.values()).filter(t => t.widgets && t.widgets.length > 0);
  
  console.log(`\n${'='.repeat(60)}`);
  console.log(`📊 Discovery Results`);
  console.log(`   Domains searched: ${checked}`);
  console.log(`   With AI chatbots: ${withWidgets}`);
  console.log(`   Detection rate: ${checked > 0 ? Math.round(withWidgets/checked*100) : 0}%`);
  
  if (results.length > 0) {
    console.log(`\n   🤖 Targets with chatbots:\n`);
    for (const r of results) {
      console.log(`   ${r.domain}`);
      console.log(`      Widgets: ${r.widgets.join(', ')}`);
      console.log(`      URL: ${r.url}`);
      console.log(`      Source: ${r.source}`);
      console.log();
    }
    
    console.log(`\n   Next steps:`);
    console.log(`   1. Visit these URLs with the Chrome extension to test chatbots`);
    console.log(`   2. Use the CLI: drift probe --url <url>`);
    console.log(`   3. Run the spider for deeper analysis: node src/spider.js <url> --deep`);
  }
  
  return { checked, withWidgets, results };
}

// CLI parsing
const args = process.argv.slice(2);

if (args.length === 0) {
  console.log(`
🔍 Agent Drift — Discovery Engine

Find AI chatbots in the wild and test them for vulnerabilities.

Usage:
  node src/discover.js --industry <sector>     Search by industry
  node src/discover.js --company <name>        Search specific company  
  node src/discover.js --dork <query>          Custom Google dork
  node src/discover.js --shodan <query>        Shodan infrastructure search
  node src/discover.js --list <file>           Check URLs from file

Options:
  --region <country>   Filter by region (UK, US, etc.)
  --limit <n>          Max targets to check (default: 30)
  --output <file>      Save results as JSON

Industries: insurance, banking, healthcare, ecommerce, saas, travel, telecom

Environment:
  BRAVE_API_KEY      Brave Search API key (required for web search)
  SHODAN_API_KEY     Shodan API key (optional, for infrastructure search)

Examples:
  node src/discover.js --industry insurance --region UK --limit 50
  node src/discover.js --company "chipotle"
  node src/discover.js --dork 'intext:"powered by Intercom"' --limit 20
  node src/discover.js --shodan intercom
  node src/discover.js --list fortune500-urls.txt --output results.json
`);
  process.exit(0);
}

const options = {};
for (let i = 0; i < args.length; i += 2) {
  const key = args[i].replace('--', '');
  options[key] = args[i + 1];
}
if (options.limit) options.limit = parseInt(options.limit);

const { checked, withWidgets, results } = await discover(options);

if (options.output) {
  writeFileSync(options.output, JSON.stringify(results, null, 2));
  console.log(`\n💾 Results saved to ${options.output}`);
}
