// Test du coeur JS (extrait de index.html) avec des données fictives.
// Usage : node tests/test_core.js
const fs = require('fs'), path = require('path'), assert = require('assert');
const html = fs.readFileSync(path.join(__dirname, '..', 'index.html'), 'utf8');
const src = html.slice(html.indexOf('/* ===== CORE'), html.indexOf('/* ===== UI ===== */'));
const { generate, MODS } = new Function(src + '; return { generate, MODS };')();
const NOW = '2026-01-01 00:00:00';

// Production : ordre des balises, Id/TS conservés, nettoyage espaces et ligatures
let r = generate('Production', [['Id','Name','Category','DateLimit'], ['000123456789012345','BACON DE BŒUF ','Viandes',24]], {}, NOW);
assert.deepStrictEqual(r.errs, []);
assert.ok(r.xml.includes('<Id>000123456789012345</Id>'), 'zéros initiaux conservés');
assert.ok(r.xml.includes('<Name>BACON DE BOEUF</Name>'), 'ligature et espace nettoyés');
assert.ok(r.xml.indexOf('<idFileAttente>') < r.xml.indexOf('<Id>'));
assert.ok(!r.xml.includes('\r'), 'Production en LF');

// Id générés : 18 chiffres, uniques
r = generate('Production', [['Name','DateLimit'], ['A',-1], ['B',-1]], {}, NOW);
const ids = [...r.xml.matchAll(/<Id>(\d+)<\/Id>/g)].map(m => m[1]);
assert.strictEqual(new Set(ids).size, 2); ids.forEach(i => assert.strictEqual(i.length, 18));

// Service : CRLF, Delete forcé à false
r = generate('Service', [['Name','TempMin','TempMax','Delete'], ['Soupe',65,90,'true']], {}, NOW);
assert.ok(r.xml.includes('\r\n') && r.xml.includes('<Delete>false</Delete>'));

// Erreurs : champ obligatoire, nombre invalide, doublon d'Id
r = generate('Service', [['Name','TempMin','TempMax'], ['', 1, 2], ['X','a',2]], {}, NOW);
assert.strictEqual(r.xml, null); assert.ok(r.errs.length >= 2);
r = generate('Production', [['Id','Name','DateLimit'], ['1','A',1], ['1','B',1]], {}, NOW);
assert.strictEqual(r.xml, null);

// Stickers : DLType, IsDDM, règle Boulangerie Ange
const st = [['Name','Category','DateLimit'], ['A','DDM SECONDAIRE',72], ['B','Sauces',48], ['C','Sauces',-1]];
r = generate('Stickers', st, { dltype: '2', isddm: 'false', excCat: 'DDM SECONDAIRE', excVal: 'true' }, NOW);
assert.deepStrictEqual(r.errs, []);
assert.deepStrictEqual([...r.xml.matchAll(/<IsDDM>(\w+)/g)].map(m => m[1]), ['true','false','false']);
assert.deepStrictEqual([...r.xml.matchAll(/<DLType>(-?\d)/g)].map(m => m[1]), ['2','2','-1']);
r = generate('Stickers', st, { dltype: '', isddm: 'false' }, NOW);
assert.ok(r.errs.length, 'DLType requis si DateLimit autre que -1');
r = generate('Stickers', [['Name','DateLimit'], ['A',-1]], { dltype: '', isddm: 'false' }, NOW);
assert.deepStrictEqual(r.errs, [], 'DLType inutile si tout est à -1');

// Idempotence de forme : tous les modules produisent un XML bien formé
for (const n of Object.keys(MODS)) {
  const hdr = MODS[n].req, row = hdr.map(t => t === 'Name' ? 'Test' : 1);
  r = generate(n, [hdr, row], { dltype: '0', isddm: 'false' }, NOW);
  assert.deepStrictEqual(r.errs, [], n);
  assert.ok(r.xml.startsWith('<?xml') && r.xml.includes(`</ArrayOf${MODS[n].el}>`), n);
}
console.log('OK : tests du coeur JS passés');
