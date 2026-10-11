import test from 'node:test';
import assert from 'node:assert/strict';
import {
  addMinutesIso, DAY_START_MIN, eventLayout, filterItems, groupActions, itemsOnDay,
  isOrganizerCommand, monthCells, overdueItems, parseOrganizerCommand, parseQuickAddClient,
  filterPendingMail, pendingMailVisible, PX_PER_MIN, shouldOfferCrewDraft, showsWorkroomJobs, snapMinutes,
  timeFromOffset, weekDays,
} from './organizer-logic.ts';

test('filter by job, person, kind', () => {
  const items = [
    { id: '1', title: 'Install Marley', kind: 'install', job_id: 'j1', assigned_resource_ids: ['r1'] },
    { id: '2', title: 'Call Ana', kind: 'call', job_id: 'j2', assigned_resource_ids: ['r2'] },
  ];
  assert.equal(filterItems(items, { jobId: 'j1' }).length, 1);
  assert.equal(filterItems(items, { resourceId: 'r2' })[0].id, '2');
  assert.equal(filterItems(items, { kind: 'install' })[0].title.includes('Marley'), true);
  assert.equal(filterItems(items, { query: 'ana' })[0].id, '2');
  const mixed = [
    ...items,
    { id: '3', title: 'Kids recital', kind: 'school', space_id: 'family' },
  ];
  assert.equal(filterItems(mixed, { spaceId: 'family' })[0].id, '3');
});

test('overdue vs today', () => {
  const items = [
    { id: 'a', title: 'Late', due_at: '2026-10-01T09:00:00', status: 'open' },
    { id: 'b', title: 'Done late', due_at: '2026-10-01T09:00:00', status: 'done' },
    { id: 'c', title: 'Today', start_time: '2026-10-11T10:00:00', status: 'planned' },
  ];
  const over = overdueItems(items, '2026-10-11T00:00:00');
  assert.deepEqual(over.map((i) => i.id), ['a']);
  assert.equal(itemsOnDay(items, '2026-10-11').length, 1);
});

test('quick-add parse Friday 2pm / install', () => {
  const friday = new Date(2026, 9, 16);
  const call = parseQuickAddClient('call Marley Friday 2pm', friday);
  assert.equal(call.kind, 'call');
  assert.equal(call.start_time, '2026-10-16T14:00:00');
  const inst = parseQuickAddClient('schedule install for the Marley job Friday 10am', friday);
  assert.equal(inst.kind, 'install');
  assert.equal(inst.start_time, '2026-10-16T10:00:00');
});

test('drag snap and resize math', () => {
  assert.equal(snapMinutes(67), 60);
  assert.equal(snapMinutes(70), 75);
  assert.equal(timeFromOffset('2026-10-17', 0), '2026-10-17T07:00:00');
  const later = addMinutesIso('2026-10-17T10:00:00', 90);
  assert.ok(later.includes('11:30'));
});

test('event layout on day grid', () => {
  const lay = eventLayout(
    { id: '1', title: 'x', start_time: '2026-10-17T09:00:00', end_time: '2026-10-17T11:00:00' },
    '2026-10-17',
  );
  assert.ok(lay);
  assert.equal(lay.top, (9 * 60 - DAY_START_MIN) * PX_PER_MIN);
  assert.equal(lay.height, 120 * PX_PER_MIN);
  assert.equal(eventLayout({ id: '1', title: 'x', start_time: '2026-10-18T09:00:00' }, '2026-10-17'), null);
});

test('week and month cells', () => {
  const week = weekDays(new Date(2026, 9, 16));
  assert.equal(week.length, 7);
  assert.equal(week[0].getDay(), 0);
  const cells = monthCells(new Date(2026, 9, 1));
  assert.equal(cells.length % 7, 0);
  assert.equal(cells.filter((c) => c.inMonth).length, 31);
});

test('NL command: move + tell the crew', () => {
  const cmd = parseOrganizerCommand("move Marley's install to Friday and tell the crew");
  assert.equal(cmd.command, 'move');
  assert.equal(cmd.tell_crew, true);
  assert.equal(isOrganizerCommand("call Marley Friday 2pm"), false);
  assert.equal(isOrganizerCommand('request deposit for Marley'), true);
});

test('action groups and crew-draft after drag', () => {
  const groups = groupActions([
    { id: 'navigate', label: 'Navigate', group: 'stop' },
    { id: 'send_quote', label: 'Send quote', group: 'job', draft: true },
    { id: 'approve_send', label: 'Approve & Send', group: 'followup', requires_confirm: true },
  ]);
  assert.equal(groups.stop[0].id, 'navigate');
  assert.equal(groups.job[0].draft, true);
  assert.equal(groups.followup[0].requires_confirm, true);
  assert.equal(shouldOfferCrewDraft(true, false), true);
  assert.equal(shouldOfferCrewDraft(true, true), false);
  assert.equal(showsWorkroomJobs({ allows_workroom_jobs: true }, ''), true);
  assert.equal(showsWorkroomJobs({ allows_workroom_jobs: true }, 'family'), false);
  assert.equal(showsWorkroomJobs({ allows_workroom_jobs: false }, 'workroom'), false);
});

test('pending mail hides snoozed ids', () => {
  const rows = [
    { id: 'gmail:1', source: 'gmail', message_id: '1', subject: 'Quote?', space_id: 'workroom' },
    { id: 'outlook:2', source: 'outlook', message_id: '2', subject: 'School', space_id: 'family', from_name: 'Office' },
  ];
  assert.equal(pendingMailVisible(rows).length, 2);
  assert.deepEqual(pendingMailVisible(rows, ['gmail:1']).map((m) => m.id), ['outlook:2']);
  assert.deepEqual(filterPendingMail(rows, { spaceId: 'family' }).map((m) => m.id), ['outlook:2']);
  assert.deepEqual(filterPendingMail(rows, { query: 'school' }).map((m) => m.id), ['outlook:2']);
});
