#!/usr/bin/env node
/**
 * Sitemap generator for OmniMigrate frontend
 * Runs after build to generate sitemap.xml and robots.txt in dist/
 */

import fs from 'fs';
import path from 'path';

const BASE_URL = process.env.VITE_SITE_URL || 'https://omnimigrate.app';
const BUILD_DIR = path.resolve(process.cwd(), 'dist');

const STATIC_ROUTES = [
  { path: '', changefreq: 'weekly', priority: 1.0 },
  { path: '/demo', changefreq: 'monthly', priority: 0.8 },
  { path: '/login', changefreq: 'yearly', priority: 0.3 },
  { path: '/register', changefreq: 'yearly', priority: 0.3 },
  { path: '/forgot-password', changefreq: 'yearly', priority: 0.2 },
  { path: '/reset-password', changefreq: 'yearly', priority: 0.2 },
  { path: '/docs', changefreq: 'weekly', priority: 0.6 },
  { path: '/pricing', changefreq: 'monthly', priority: 0.7 },
  { path: '/features', changefreq: 'monthly', priority: 0.6 },
  { path: '/about', changefreq: 'yearly', priority: 0.3 },
  { path: '/contact', changefreq: 'monthly', priority: 0.4 },
  { path: '/privacy', changefreq: 'yearly', priority: 0.2 },
  { path: '/terms', changefreq: 'yearly', priority: 0.2 },
  { path: '/security', changefreq: 'monthly', priority: 0.4 },
  { path: '/changelog', changefreq: 'weekly', priority: 0.5 },
];

// Protected routes (require auth) - lower priority, noindex via robots
const PROTECTED_ROUTES = [
  { path: '/dashboard', changefreq: 'daily', priority: 0.5 },
  { path: '/projects', changefreq: 'daily', priority: 0.6 },
  { path: '/upload', changefreq: 'weekly', priority: 0.6 },
  { path: '/jobs', changefreq: 'daily', priority: 0.5 },
  { path: '/autonomous', changefreq: 'weekly', priority: 0.5 },
  { path: '/organizations', changefreq: 'monthly', priority: 0.4 },
  { path: '/settings', changefreq: 'monthly', priority: 0.3 },
  { path: '/admin', changefreq: 'yearly', priority: 0.1 },
];

function generateSitemap() {
  const today = new Date().toISOString().split('T')[0];
  
  const urls = [
    ...STATIC_ROUTES.map(route => ({
      url: `${BASE_URL}${route.path}`,
      lastmod: today,
      changefreq: route.changefreq,
      priority: route.priority,
    })),
    ...PROTECTED_ROUTES.map(route => ({
      url: `${BASE_URL}${route.path}`,
      lastmod: today,
      changefreq: route.changefreq,
      priority: route.priority,
    })),
  ];

  const sitemap = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"
        xmlns:xhtml="http://www.w3.org/1999/xhtml">
${urls.map(url => `  <url>
    <loc>${url.url}</loc>
    <lastmod>${url.lastmod}</lastmod>
    <changefreq>${url.changefreq}</changefreq>
    <priority>${url.priority}</priority>
  </url>`).join('\n')}
</urlset>`;

  return sitemap;
}

function generateRobots() {
  return `# Robots.txt for OmniMigrate
User-agent: *
Allow: /

# Disallow protected/auth routes
Disallow: /dashboard/
Disallow: /projects/
Disallow: /upload/
Disallow: /jobs/
Disallow: /autonomous/
Disallow: /organizations/
Disallow: /settings/
Disallow: /admin/
Disallow: /login
Disallow: /register
Disallow: /forgot-password
Disallow: /reset-password

# Sitemap
Sitemap: ${BASE_URL}/sitemap.xml

# Host
Host: ${BASE_URL.replace('https://', '').replace('http://', '')}
`;
}

function main() {
  console.log('Generating sitemap.xml and robots.txt...');
  
  if (!fs.existsSync(BUILD_DIR)) {
    console.error(`Build directory not found: ${BUILD_DIR}`);
    console.error('Run "npm run build" first.');
    process.exit(1);
  }

  const sitemap = generateSitemap();
  const robots = generateRobots();

  fs.writeFileSync(path.join(BUILD_DIR, 'sitemap.xml'), sitemap);
  fs.writeFileSync(path.join(BUILD_DIR, 'robots.txt'), robots);

  console.log('✅ sitemap.xml generated');
  console.log('✅ robots.txt generated');
  console.log(`📁 Files written to: ${BUILD_DIR}`);
}

main();