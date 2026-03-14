#!/usr/bin/env node
/**
 * Agent Drift — Web Spider
 * Crawls websites to find and test AI chatbot widgets.
 * 
 * Usage:
 *   drift-spider https://example.com
 *   drift-spider --list urls.txt --output report.json
 *   drift-spider https://example.com --deep (follows links on same domain)
 */

import { JSDOM } from 'jsdom';

const WIDGET_SIGNATURES = [
  // Intercom
  { name: 'Intercom', patterns: ['intercom', 'widget.intercom.io', 'intercom-container'] },
  // Drift
  { name: 'Drift', patterns: ['drift.com', 'drift-widget', 'js.driftt.com'] },
  // Zendesk
  { name: 'Zendesk', patterns: ['zendesk', 'zdassets.com', 'zopim', 'web_widget'] },
  // Tidio
  { name: 'Tidio', patterns: ['tidio', 'tidiochat'] },
  // Crisp
  { name: 'Crisp', patterns: ['crisp.chat', 'crisp-client'] },
  // HubSpot
  { name: 'HubSpot', patterns: ['hubspot', 'hs-scripts', 'hubspot-messages'] },
  // Freshdesk/Freshchat
  { name: 'Freshdesk', patterns: ['freshdesk', 'freshchat', 'freshworks'] },
  // LiveChat
  { name: 'LiveChat', patterns: ['livechat', 'livechatinc'] },
  // Chatbot.com
  { name: 'Chatbot.com', patterns: ['chatbot.com', 'livechatbot'] },
  // Ada
  { name: 'Ada', patterns: ['ada.cx', 'ada-chat'] },
  // Kustomer
  { name: 'Kustomer', patterns: ['kustomer', 'chat.kustomerapp'] },
  // Custom / Generic
  { name: 'Custom AI Chat', patterns: ['chatbot', 'chat-widget', 'ai-assistant', 'virtual-assistant'] },
  // OpenAI
  { name: 'OpenAI Widget', patterns: ['openai', 'chatgpt'] },
];

async function fetchPage(url) {
  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    
    const res = await fetch(url, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'Mozilla/5.0 (compatible; AgentDrift/1.0; +https://github.com/jhammant/agent-drift)',
      },
    });
    clearTimeout(timeout);
    
    if (!res.ok) return null;
    return await res.text();
  } catch (e) {
    return null;
  }
}

function detectWidgets(html, url) {
  const found = [];
  const htmlLower = html.toLowerCase();
  
  for (const sig of WIDGET_SIGNATURES) {
    for (const pattern of sig.patterns) {
      if (htmlLower.includes(pattern.toLowerCase())) {
        found.push({
          widget: sig.name,
          pattern,
          url,
          confidence: htmlLower.split(pattern.toLowerCase()).length - 1, // occurrence count
        });
        break; // one match per widget type is enough
      }
    }
  }
  
  // Check for iframes with chat-related titles
  try {
    const dom = new JSDOM(html);
    const iframes = dom.window.document.querySelectorAll('iframe');
    for (const iframe of iframes) {
      const title = (iframe.getAttribute('title') || '').toLowerCase();
      const src = (iframe.getAttribute('src') || '').toLowerCase();
      if (title.includes('chat') || title.includes('support') || title.includes('help') ||
          src.includes('chat') || src.includes('bot')) {
        found.push({
          widget: 'Chat iframe',
          pattern: `iframe: ${title || src}`,
          url,
          confidence: 1,
        });
      }
    }
  } catch (e) { /* parsing errors are ok */ }
  
  return found;
}

function extractLinks(html, baseUrl) {
  try {
    const dom = new JSDOM(html);
    const links = dom.window.document.querySelectorAll('a[href]');
    const base = new URL(baseUrl);
    const urls = new Set();
    
    for (const link of links) {
      try {
        const href = new URL(link.getAttribute('href'), baseUrl);
        if (href.hostname === base.hostname && href.protocol.startsWith('http')) {
          urls.add(href.origin + href.pathname);
        }
      } catch (e) { /* invalid URLs */ }
    }
    
    return Array.from(urls).slice(0, 50); // limit crawl
  } catch (e) {
    return [];
  }
}

async function spider(urls, options = {}) {
  const { deep = false, maxPages = 20 } = options;
  const visited = new Set();
  const results = [];
  const queue = [...urls];
  
  console.log(`🕷️  Agent Drift Spider`);
  console.log(`   Scanning ${urls.length} URL(s)${deep ? ' (deep mode)' : ''}...\n`);
  
  while (queue.length > 0 && visited.size < maxPages) {
    const url = queue.shift();
    if (visited.has(url)) continue;
    visited.add(url);
    
    process.stdout.write(`   Checking: ${url.substring(0, 60)}...`);
    
    const html = await fetchPage(url);
    if (!html) {
      console.log(' ❌ failed');
      continue;
    }
    
    const widgets = detectWidgets(html, url);
    if (widgets.length > 0) {
      console.log(` ✅ Found: ${widgets.map(w => w.widget).join(', ')}`);
      results.push(...widgets);
    } else {
      console.log(' —');
    }
    
    // Deep mode: follow links on same domain
    if (deep && visited.size < maxPages) {
      const links = extractLinks(html, url);
      for (const link of links) {
        if (!visited.has(link)) {
          queue.push(link);
        }
      }
    }
  }
  
  return { visited: visited.size, results };
}

// CLI
const args = process.argv.slice(2);

if (args.length === 0) {
  console.log('Usage: node spider.js <url> [--deep] [--max-pages 20]');
  console.log('       node spider.js --list urls.txt');
  process.exit(0);
}

let urls = [];
let deep = args.includes('--deep');
let maxPages = 20;

const maxIdx = args.indexOf('--max-pages');
if (maxIdx !== -1 && args[maxIdx + 1]) {
  maxPages = parseInt(args[maxIdx + 1]);
}

const listIdx = args.indexOf('--list');
if (listIdx !== -1 && args[listIdx + 1]) {
  const fs = await import('fs');
  urls = fs.readFileSync(args[listIdx + 1], 'utf-8').split('\n').filter(Boolean);
} else {
  urls = args.filter(a => a.startsWith('http'));
}

if (urls.length === 0) {
  console.log('Error: No URLs provided');
  process.exit(1);
}

const { visited, results } = await spider(urls, { deep, maxPages });

console.log(`\n${'='.repeat(60)}`);
console.log(`📊 Spider Results`);
console.log(`   Pages scanned: ${visited}`);
console.log(`   Widgets found: ${results.length}`);

if (results.length > 0) {
  console.log(`\n   Widgets:`);
  const unique = new Map();
  for (const r of results) {
    const key = `${r.widget}|${r.url}`;
    if (!unique.has(key)) unique.set(key, r);
  }
  for (const [, r] of unique) {
    console.log(`   🤖 ${r.widget} on ${r.url}`);
  }
  
  console.log(`\n   Next step: Visit these URLs and run the extension to test the chatbots.`);
  console.log(`   Or use the CLI: drift probe --url <url>`);
}
console.log();
