// Build: readable index.html  ->  dist/index.html (minified + lightly obfuscated).
// Only the single inline app IIFE is processed. CDN <script src> tags, HTML and CSS are left to html-minifier.
// Obfuscation is deliberately LIGHT: no control-flow flattening / dead-code / self-defending,
// because this app runs a 60fps WebGL loop and those transforms add runtime cost.
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs';
import { minify as terserMinify } from 'terser';
import JsObfuscator from 'javascript-obfuscator';
import { minify as htmlMinify } from 'html-minifier-terser';

const ROOT = new URL('../', import.meta.url).pathname;
const src = readFileSync(ROOT + 'index.html', 'utf8');

// isolate the one bare inline <script>…</script> (CDN tags are <script src=...>)
const open = '<script>\n';
const i = src.indexOf(open);
if (i < 0) throw new Error('inline <script> not found');
const j = src.indexOf('</script>', i);
if (j < 0) throw new Error('closing </script> not found');
const before = src.slice(0, i + open.length);
const js = src.slice(i + open.length, j);
const after = src.slice(j);

const ob0 = JsObfuscator.obfuscate(js, {
  compact: true,
  controlFlowFlattening: false,
  deadCodeInjection: false,
  debugProtection: false,
  disableConsoleOutput: false,
  identifierNamesGenerator: 'mangled',
  numbersToExpressions: false,
  renameGlobals: false,
  renameProperties: false,
  selfDefending: false,
  simplify: true,
  splitStrings: false,
  stringArray: false,          // the GLSL shaders dominate the bytes; array indirection only bloats
  stringArrayThreshold: 0,
  transformObjectKeys: false,
  unicodeEscapeSequence: false
}).getObfuscatedCode();

// terser last, so the final file is actually minified (smaller), on top of the obfuscation pass
const t = await terserMinify(ob0, {
  ecma: 2020,
  compress: { passes: 2, drop_debugger: true },
  mangle: { toplevel: true },
  format: { comments: false }
});
if (t.error) throw t.error;
const ob = t.code;

const doc = before + ob + '\n' + after;
const out = await htmlMinify(doc, {
  collapseWhitespace: true,
  removeComments: true,
  minifyCSS: true,
  minifyJS: false,            // JS already handled above
  keepClosingSlash: false,
  removeAttributeQuotes: false
});

mkdirSync(ROOT + 'dist', { recursive: true });
writeFileSync(ROOT + 'dist/index.html', out);
const kb = n => (n / 1024).toFixed(0) + ' KB';
console.log(`js ${kb(js.length)} -> obf ${kb(ob0.length)} -> terser ${kb(ob.length)}`);
console.log(`doc ${kb(src.length)} -> dist/index.html ${kb(out.length)}`);
