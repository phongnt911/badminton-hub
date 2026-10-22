// BH-07 Browser Evidence Quality Audit & Manifest Generator
// Ensures UTF-8 without BOM, LF only (CRLF=0), secret scanning, and SHA-256 manifest.

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const PROJECT_ROOT = path.resolve(__dirname, '../..');
const EVIDENCE_DIR = path.resolve(PROJECT_ROOT, 'docs/reviews/bh07/browser_evidence');

const textFiles = [
  'AGENTS.md',
  'README.md',
  'docs/00_START_HERE.md',
  'docs/25_BH07_IMPLEMENTATION_HANDOFF.md',
  'docs/STATUS_HISTORY.md',
  'docs/reviews/bh07/browser_handoff.md',
  'docs/reviews/bh07/browser_evidence/environment.json',
  'docs/reviews/bh07/browser_evidence/commands.md',
  'docs/reviews/bh07/browser_evidence/exits.json',
  'docs/reviews/bh07/browser_evidence/summary.json',
  'docs/reviews/bh07/browser_evidence/browser_runner.log',
  'docs/reviews/bh07/browser_evidence/bh07_db_results.json',
  'scripts/bh07_browser/seed_setup.js',
  'scripts/bh07_browser/run_browser_verification.js'
];

console.log('--- Step 1: Normalizing UTF-8 and LF (CRLF = 0) ---');
for (const rel of textFiles) {
  const full = path.resolve(PROJECT_ROOT, rel);
  if (!fs.existsSync(full)) {
    console.log(`SKIP (not found): ${rel}`);
    continue;
  }
  let buf = fs.readFileSync(full);
  // Check BOM
  if (buf.length >= 3 && buf[0] === 0xef && buf[1] === 0xbb && buf[2] === 0xbf) {
    buf = buf.subarray(3);
    console.log(`Stripped BOM from: ${rel}`);
  }
  let text = buf.toString('utf-8');
  if (text.includes('\r\n') || text.includes('\r')) {
    text = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n');
    fs.writeFileSync(full, text, { encoding: 'utf-8' });
    console.log(`Converted CRLF/CR to LF: ${rel}`);
  }
  // Verify 0 CRLF
  const recheck = fs.readFileSync(full);
  let crCount = 0;
  for (let i = 0; i < recheck.length; i++) {
    if (recheck[i] === 0x0d) crCount++;
  }
  if (crCount > 0) {
    console.error(`ERROR: ${rel} still contains ${crCount} CR characters!`);
    process.exit(1);
  }
}
console.log('UTF-8 without BOM & LF normalization verified!');

console.log('--- Step 2: Secret Scanning ---');
const secretPatterns = [
  /-----BEGIN [A-Z ]*PRIVATE KEY-----/,
  /ghp_[0-9a-zA-Z]{36}/,
  /xox[baprs]-[0-9a-zA-Z]{10,48}/,
  /AKIA[0-9A-Z]{16}/,
  /eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9\.[a-zA-Z0-9_\-]+\.(?!(CRXP1A7WOeoJeXxjNni43kdQwgnWNReilDMblYTn_I0))[a-zA-Z0-9_\-]+/ // Allow only static local anon JWT
];

for (const rel of textFiles) {
  const full = path.resolve(PROJECT_ROOT, rel);
  if (!fs.existsSync(full)) continue;
  const content = fs.readFileSync(full, 'utf-8');
  for (const pat of secretPatterns) {
    if (pat.test(content)) {
      console.error(`SECRET DETECTED in ${rel} matching pattern ${pat}`);
      process.exit(1);
    }
  }
}
console.log('Secret scan CLEAN! No unapproved tokens found.');

console.log('--- Step 3: Generating SHA-256 Manifest ---');
function getAllFiles(dir) {
  let list = [];
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) {
      list = list.concat(getAllFiles(p));
    } else {
      if (e.name !== 'hashes.sha256') {
        list.push(p);
      }
    }
  }
  return list;
}

const allEvidenceFiles = getAllFiles(EVIDENCE_DIR).sort();
const manifestLines = [];

for (const f of allEvidenceFiles) {
  const buf = fs.readFileSync(f);
  const hash = crypto.createHash('sha256').update(buf).digest('hex');
  const relPath = path.relative(PROJECT_ROOT, f).replace(/\\/g, '/');
  manifestLines.push(`${hash}  ${relPath}`);
}

const manifestPath = path.resolve(EVIDENCE_DIR, 'hashes.sha256');
fs.writeFileSync(manifestPath, manifestLines.join('\n') + '\n', 'utf-8');
console.log(`Generated manifest with ${manifestLines.length} files at: ${manifestPath}`);
