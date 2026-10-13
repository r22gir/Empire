import assert from 'node:assert/strict';
import test from 'node:test';
import { chatFileCategory, fileViewUrl, isChatImageFilename } from './chatFiles.ts';

test('PDFs with accents, spaces and parentheses use documents + encodeURIComponent', () => {
  const names = [
    'MeEncontreUnArcoIris (1).pdf',
    'MeEncontréUnArcoIrisPropuestaSAGAen9libros.pdf',
    'EcosistemaAMP-MeEncontreUnArcoiris.pdf',
  ];
  for (const name of names) {
    assert.equal(chatFileCategory(name), 'documents');
    assert.equal(isChatImageFilename(name), false);
    const url = fileViewUrl(name, 'http://example.test/api/v1');
    assert.match(url, /\/files\/view\/documents\//);
    assert.ok(url.includes(encodeURIComponent(name)));
    assert.equal(url.includes(' '), false);
  }
});

test('images stay on the images category', () => {
  const url = fileViewUrl('foto vacaciones.png', '/api/v1');
  assert.equal(url, `/api/v1/files/view/images/${encodeURIComponent('foto vacaciones.png')}`);
});
