import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import test from 'node:test';
import {
  DEFAULT_INTERVAL_MS,
  SLIDE_COUNT,
  WELCOME_HELP_LABEL,
  WELCOME_SKIP_ARIA,
  WELCOME_SKIP_LABEL,
  autoAdvanceEnabled,
  defaultWelcomeDeck,
  familyWelcomeAssistant,
  isLastSlide,
  nextSlideIndex,
  prevSlideIndex,
  replayRequested,
  sanitizeWelcomeImage,
  shouldShowFamilyWelcome,
  welcomePayloadLooksPrivate,
} from './familyWelcome.ts';

const here = dirname(fileURLToPath(import.meta.url));

function leakHits(deck: { slides: Array<{ title: string; body: string }> }) {
  const re = /\b(nit|rut|sas|llc|escritura|argos campestre|workroom|studio\.empirebox|founder pin)\b/i;
  return deck.slides.flatMap((slide) => re.exec(`${slide.title} ${slide.body}`) || []);
}

test('family decks are six Spanish slides and differ by assistant', () => {
  const amp = defaultWelcomeDeck('amp');
  const maxine = defaultWelcomeDeck('maxine');
  assert.equal(amp.slides.length, SLIDE_COUNT);
  assert.equal(maxine.slides.length, SLIDE_COUNT);
  assert.equal(amp.interval_ms, DEFAULT_INTERVAL_MS);
  assert.equal(familyWelcomeAssistant('amp'), 'Max-e');
  assert.equal(familyWelcomeAssistant('maxine'), 'Maxine');
  assert.match(amp.slides[0].title, /Hola, soy Max-e/);
  assert.match(maxine.slides[0].title, /Hola, soy Maxine/);
  assert.match(amp.slides[1].body, /hermanos/);
  assert.match(amp.slides[3].body, /Pedir ayuda a Max/);
  assert.match(amp.slides[4].body, /20%/);
  assert.equal(leakHits(amp).length, 0);
  assert.equal(leakHits(maxine).length, 0);
  const seedAmp = JSON.parse(readFileSync(join(here, '../../../deploy/seeds/amp-welcome.json'), 'utf8'));
  const libAmp = JSON.parse(readFileSync(join(here, 'welcome/amp.json'), 'utf8'));
  assert.deepEqual(amp, seedAmp);
  assert.deepEqual(amp, libAmp);
});

test('overlay stays off Workroom, login, and already-seen users unless replay', () => {
  assert.equal(shouldShowFamilyWelcome({ edition: 'workroom', pathname: '/', seen: false }), false);
  assert.equal(shouldShowFamilyWelcome({
    edition: 'workroom', host: 'studio.empirebox.store', pathname: '/', seen: false,
  }), false);
  assert.equal(shouldShowFamilyWelcome({ edition: 'amp', host: 'amp.empirebox.store', pathname: '/login', seen: false }), false);
  assert.equal(shouldShowFamilyWelcome({ edition: 'amp', host: 'amp.empirebox.store', pathname: '/', seen: false }), true);
  assert.equal(shouldShowFamilyWelcome({ edition: 'maxine', host: 'maxine.empirebox.store', pathname: '/', seen: true }), false);
  assert.equal(shouldShowFamilyWelcome({
    edition: 'maxine', host: 'maxine.empirebox.store', pathname: '/', seen: true, replay: true,
  }), true);
  assert.equal(replayRequested('?bienvenida=1'), true);
  assert.equal(replayRequested('?theme=gold'), false);
});

test('slideshow controls and reduced motion', () => {
  assert.equal(autoAdvanceEnabled(false, true), true);
  assert.equal(autoAdvanceEnabled(true, true), false);
  assert.equal(autoAdvanceEnabled(false, false), false);
  assert.equal(nextSlideIndex(0, 6), 1);
  assert.equal(nextSlideIndex(5, 6), 5);
  assert.equal(prevSlideIndex(0), 0);
  assert.equal(prevSlideIndex(2), 1);
  assert.equal(isLastSlide(5, 6), true);
  assert.equal(isLastSlide(4, 6), false);
  assert.equal(WELCOME_HELP_LABEL, 'Ver bienvenida');
  assert.equal(WELCOME_SKIP_LABEL, 'Saltar');
  assert.equal(WELCOME_SKIP_ARIA, 'Saltar / Skip');
});

test('images stay same-origin and payloads never list other users', () => {
  assert.equal(sanitizeWelcomeImage('/welcome/amp/01.jpg'), '/welcome/amp/01.jpg');
  assert.equal(sanitizeWelcomeImage('https://evil.example/x.png'), '');
  assert.equal(sanitizeWelcomeImage('//maxine.empirebox.store/x'), '');
  assert.equal(sanitizeWelcomeImage('/welcome/../amp/x'), '');
  assert.equal(welcomePayloadLooksPrivate({ slides: [], users: { a: true } }), false);
  assert.equal(welcomePayloadLooksPrivate({ slides: [], email: 'a@b.c' }), false);
  assert.equal(welcomePayloadLooksPrivate({ slides: [] }), true);
});
