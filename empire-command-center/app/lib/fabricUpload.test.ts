import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { FABRIC_MAX_BYTES, fabricTooLarge, fabricUploadKind, isFabricImage } from './fabricUpload.ts';
import { COMMAND_CENTER_DOCUMENT_TITLE, LUXE_DOCUMENT_TITLE, documentTitleForHost } from './luxeDocumentTitle.ts';

test('fabric photos include HEIC and any other file goes to scans', () => {
  assert.equal(isFabricImage({ name: 'IMG_1.HEIC', type: '' }), true);
  assert.equal(isFabricImage({ name: 'shot.jpg', type: 'image/jpeg' }), true);
  assert.equal(isFabricImage({ name: 'swatch.png', type: 'image/png' }), true);
  assert.equal(fabricUploadKind({ name: 'IMG_1.HEIC', type: '' }), 'photos');
  assert.equal(fabricUploadKind({ name: 'notes.pdf', type: 'application/pdf' }), 'scans');
  assert.equal(FABRIC_MAX_BYTES, 200 * 1024 * 1024);
  assert.equal(fabricTooLarge({ size: FABRIC_MAX_BYTES }), false);
  assert.equal(fabricTooLarge({ size: FABRIC_MAX_BYTES + 1 }), true);
});

test('the fabric control is a real file input, not a script-built one', () => {
  const source = readFileSync(new URL('../components/intake/FabricInfoSection.tsx', import.meta.url), 'utf8');
  assert.equal(source.includes("document.createElement('input')"), false);
  assert.equal(source.includes('type="file"'), true);
  assert.equal(source.includes('multiple'), true);
  assert.equal(source.includes('.heic'), true);
  assert.equal(source.includes('accept="image/*,.heic,.heif,.jpg,.jpeg,.png"'), true);
  const library = source.slice(source.lastIndexOf('ref={libraryRef}'), source.lastIndexOf('ref={libraryRef}') + 220);
  assert.equal(library.includes('accept='), false);
});

test('luxe host tab title is the designer intake title', () => {
  assert.equal(documentTitleForHost('luxe.empirebox.store'), LUXE_DOCUMENT_TITLE);
  assert.equal(documentTitleForHost('Luxe.EmpireBox.Store:443'), LUXE_DOCUMENT_TITLE);
  assert.equal(documentTitleForHost('test-luxe.empirebox.store'), LUXE_DOCUMENT_TITLE);
  assert.equal(documentTitleForHost('studio.empirebox.store'), COMMAND_CENTER_DOCUMENT_TITLE);
  assert.equal(LUXE_DOCUMENT_TITLE, 'Empire Workroom · Designer Intake');
  const page = readFileSync(new URL('../intake/project/new/page.tsx', import.meta.url), 'utf8');
  assert.equal(page.includes('analyze the photos'), false);
});
