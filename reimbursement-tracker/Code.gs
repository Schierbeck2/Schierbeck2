const SHEETS = {
  SETTINGS: 'Settings',
  PROJECTS: 'Projects',
  ENTRIES: 'TimeEntries',
  PAYMENTS: 'Payments',
};

const OWNER_YOU = 'You';
const OWNER_COWORKER = 'Coworker';

function doGet(e) {
  ensureSheets_();
  const view = (e && e.parameter && e.parameter.view) || autoView_();
  const file = view === 'owner' ? 'Owner' : 'Assistant';
  const tmpl = HtmlService.createTemplateFromFile(file);
  tmpl.userEmail = safeEmail_();
  tmpl.coworkerName = getSetting('coworkerName') || 'Coworker';
  tmpl.hourlyRate = Number(getSetting('hourlyRate') || 0);
  return tmpl.evaluate()
    .setTitle('Time & Reimbursement Tracker')
    .addMetaTag('viewport', 'width=device-width, initial-scale=1');
}

function include(name) {
  return HtmlService.createHtmlOutputFromFile(name).getContent();
}

function autoView_() {
  const email = (safeEmail_() || '').toLowerCase();
  const admins = (getSetting('adminEmails') || '')
    .split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
  return admins.includes(email) ? 'owner' : 'assistant';
}

function safeEmail_() {
  try { return Session.getActiveUser().getEmail() || ''; } catch (err) { return ''; }
}

// ---------- Sheet bootstrap ----------

function ensureSheets_() {
  const ss = SpreadsheetApp.getActive();
  const seed = {
    [SHEETS.SETTINGS]: [['key', 'value']],
    [SHEETS.PROJECTS]: [['id', 'name', 'owner', 'status']],
    [SHEETS.ENTRIES]: [['id', 'projectId', 'assistantEmail', 'clockIn', 'clockOut', 'hours', 'notes']],
    [SHEETS.PAYMENTS]: [['id', 'date', 'amount', 'note']],
  };
  Object.keys(seed).forEach(name => {
    let sh = ss.getSheetByName(name);
    if (!sh) {
      sh = ss.insertSheet(name);
      sh.getRange(1, 1, 1, seed[name][0].length).setValues(seed[name]).setFontWeight('bold');
      sh.setFrozenRows(1);
    }
  });
  const settingsSheet = ss.getSheetByName(SHEETS.SETTINGS);
  if (settingsSheet.getLastRow() < 2) {
    settingsSheet.getRange(2, 1, 4, 2).setValues([
      ['hourlyRate', 25],
      ['adminEmails', 'schierbeck@gmail.com'],
      ['coworkerName', 'Coworker'],
      ['summaryEmail', 'schierbeck@gmail.com'],
    ]);
  }
}

// ---------- Settings ----------

function getSetting(key) {
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEETS.SETTINGS);
  if (!sh) return null;
  const data = sh.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === key) return data[i][1];
  }
  return null;
}

// ---------- Projects ----------

function listProjects() {
  return readAllAsObjects_(SHEETS.PROJECTS).filter(p => p.status !== 'archived');
}

function addProject(name, owner) {
  if (!isAdmin_()) throw new Error('Not authorized');
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEETS.PROJECTS);
  sh.appendRow([Utilities.getUuid(), name, owner, 'active']);
  return listProjects();
}

function archiveProject(id) {
  if (!isAdmin_()) throw new Error('Not authorized');
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEETS.PROJECTS);
  const data = sh.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === id) sh.getRange(i + 1, 4).setValue('archived');
  }
  return listProjects();
}

// ---------- Time entries ----------

function clockIn(projectId) {
  const email = safeEmail_();
  if (!email) throw new Error('Could not determine your account');
  clockOutInternal_(email);
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEETS.ENTRIES);
  sh.appendRow([Utilities.getUuid(), projectId, email, new Date(), '', '', '']);
  return assistantState();
}

function clockOut(notes) {
  const email = safeEmail_();
  clockOutInternal_(email, notes);
  return assistantState();
}

function clockOutInternal_(email, notes) {
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEETS.ENTRIES);
  const data = sh.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (data[i][2] === email && !data[i][4]) {
      const out = new Date();
      const hrs = (out - new Date(data[i][3])) / 36e5;
      sh.getRange(i + 1, 5).setValue(out);
      sh.getRange(i + 1, 6).setValue(round2_(hrs));
      if (notes) sh.getRange(i + 1, 7).setValue(notes);
    }
  }
}

function getCurrentEntry_(email) {
  const entries = readAllAsObjects_(SHEETS.ENTRIES);
  return entries.find(e => e.assistantEmail === email && !e.clockOut) || null;
}

function assistantState() {
  const email = safeEmail_();
  const projects = listProjects();
  const current = getCurrentEntry_(email);
  const myEntries = readAllAsObjects_(SHEETS.ENTRIES)
    .filter(e => e.assistantEmail === email && e.clockOut)
    .sort((a, b) => new Date(b.clockIn) - new Date(a.clockIn))
    .slice(0, 25)
    .map(e => decorateEntry_(e, projects));
  return {
    email,
    projects,
    current: current ? decorateEntry_(current, projects) : null,
    recent: myEntries,
  };
}

function updateEntry(id, payload) {
  const email = safeEmail_();
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEETS.ENTRIES);
  const data = sh.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] !== id) continue;
    if (data[i][2] !== email && !isAdmin_()) throw new Error('Not authorized');
    const row = i + 1;
    if (payload.projectId) sh.getRange(row, 2).setValue(payload.projectId);
    if (payload.clockIn) sh.getRange(row, 4).setValue(new Date(payload.clockIn));
    if (payload.clockOut) sh.getRange(row, 5).setValue(new Date(payload.clockOut));
    if (payload.notes !== undefined) sh.getRange(row, 7).setValue(payload.notes);
    const ci = new Date(sh.getRange(row, 4).getValue());
    const co = new Date(sh.getRange(row, 5).getValue());
    if (ci && co && !isNaN(co)) {
      sh.getRange(row, 6).setValue(round2_((co - ci) / 36e5));
    }
    return assistantState();
  }
  throw new Error('Entry not found');
}

function deleteEntry(id) {
  const email = safeEmail_();
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEETS.ENTRIES);
  const data = sh.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] !== id) continue;
    if (data[i][2] !== email && !isAdmin_()) throw new Error('Not authorized');
    sh.deleteRow(i + 1);
    return assistantState();
  }
  throw new Error('Entry not found');
}

// ---------- Payments ----------

function listPayments() {
  return readAllAsObjects_(SHEETS.PAYMENTS)
    .sort((a, b) => new Date(b.date) - new Date(a.date));
}

function addPayment(date, amount, note) {
  if (!isAdmin_()) throw new Error('Not authorized');
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEETS.PAYMENTS);
  sh.appendRow([Utilities.getUuid(), new Date(date), Number(amount), note || '']);
  return ownerDashboard();
}

function deletePayment(id) {
  if (!isAdmin_()) throw new Error('Not authorized');
  const sh = SpreadsheetApp.getActive().getSheetByName(SHEETS.PAYMENTS);
  const data = sh.getDataRange().getValues();
  for (let i = 1; i < data.length; i++) {
    if (data[i][0] === id) {
      sh.deleteRow(i + 1);
      return ownerDashboard();
    }
  }
  throw new Error('Payment not found');
}

// ---------- Owner dashboard ----------

function ownerDashboard() {
  if (!isAdmin_()) throw new Error('Not authorized');
  const projects = readAllAsObjects_(SHEETS.PROJECTS);
  const entries = readAllAsObjects_(SHEETS.ENTRIES).filter(e => e.clockOut);
  const payments = listPayments();
  const rate = Number(getSetting('hourlyRate') || 0);

  const now = new Date();
  const weekStart = startOfWeek_(now);
  const monthStart = new Date(now.getFullYear(), now.getMonth(), 1);
  const yearStart = new Date(now.getFullYear(), 0, 1);

  const totals = {
    week: hoursByOwner_(entries, projects, weekStart, now),
    month: hoursByOwner_(entries, projects, monthStart, now),
    year: hoursByOwner_(entries, projects, yearStart, now),
    all: hoursByOwner_(entries, projects, new Date(0), now),
  };

  const coworkerHoursAll = totals.all[OWNER_COWORKER] || 0;
  const billed = round2_(coworkerHoursAll * rate);
  const paid = round2_(payments.reduce((s, p) => s + Number(p.amount || 0), 0));
  const balance = round2_(billed - paid);

  const recent = entries
    .sort((a, b) => new Date(b.clockIn) - new Date(a.clockIn))
    .slice(0, 50)
    .map(e => decorateEntry_(e, projects));

  return {
    rate,
    coworkerName: getSetting('coworkerName') || 'Coworker',
    totals,
    billed, paid, balance,
    recent,
    payments,
    projects,
  };
}

function hoursByOwner_(entries, projects, from, to) {
  const ownerById = Object.fromEntries(projects.map(p => [p.id, p.owner]));
  const out = { [OWNER_YOU]: 0, [OWNER_COWORKER]: 0 };
  entries.forEach(e => {
    const ci = new Date(e.clockIn);
    if (ci < from || ci > to) return;
    const owner = ownerById[e.projectId] || OWNER_YOU;
    out[owner] = (out[owner] || 0) + Number(e.hours || 0);
  });
  out[OWNER_YOU] = round2_(out[OWNER_YOU]);
  out[OWNER_COWORKER] = round2_(out[OWNER_COWORKER]);
  return out;
}

// ---------- Monthly email ----------

function sendMonthlySummary() {
  const projects = readAllAsObjects_(SHEETS.PROJECTS);
  const entries = readAllAsObjects_(SHEETS.ENTRIES).filter(e => e.clockOut);
  const payments = listPayments();
  const rate = Number(getSetting('hourlyRate') || 0);
  const to = getSetting('summaryEmail');
  if (!to) return;

  const now = new Date();
  const periodEnd = new Date(now.getFullYear(), now.getMonth(), 1);
  const periodStart = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const periodLabel = Utilities.formatDate(periodStart, Session.getScriptTimeZone(), 'MMMM yyyy');

  const monthHours = hoursByOwner_(entries, projects, periodStart, periodEnd);
  const monthBilled = round2_((monthHours[OWNER_COWORKER] || 0) * rate);

  const allHours = hoursByOwner_(entries, projects, new Date(0), now);
  const billedAll = round2_((allHours[OWNER_COWORKER] || 0) * rate);
  const paidAll = round2_(payments.reduce((s, p) => s + Number(p.amount || 0), 0));
  const balance = round2_(billedAll - paidAll);

  const coworker = getSetting('coworkerName') || 'Coworker';
  const subject = `Reimbursement summary — ${periodLabel}`;
  const body = [
    `Reimbursement summary for ${periodLabel}`,
    '',
    `Hourly rate: $${rate.toFixed(2)}`,
    '',
    `${periodLabel} hours:`,
    `  You:       ${monthHours[OWNER_YOU].toFixed(2)} hrs`,
    `  ${coworker}: ${monthHours[OWNER_COWORKER].toFixed(2)} hrs  →  $${monthBilled.toFixed(2)}`,
    '',
    `Running balance owed by ${coworker}:`,
    `  Total billed: $${billedAll.toFixed(2)}`,
    `  Total paid:   $${paidAll.toFixed(2)}`,
    `  Outstanding:  $${balance.toFixed(2)}`,
  ].join('\n');

  MailApp.sendEmail({ to, subject, body });
}

function installMonthlyTrigger() {
  ScriptApp.getProjectTriggers()
    .filter(t => t.getHandlerFunction() === 'sendMonthlySummary')
    .forEach(t => ScriptApp.deleteTrigger(t));
  ScriptApp.newTrigger('sendMonthlySummary')
    .timeBased().onMonthDay(1).atHour(8).create();
}

// ---------- Helpers ----------

function readAllAsObjects_(name) {
  const sh = SpreadsheetApp.getActive().getSheetByName(name);
  if (!sh || sh.getLastRow() < 2) return [];
  const data = sh.getDataRange().getValues();
  const headers = data[0];
  return data.slice(1).map(row => {
    const obj = {};
    headers.forEach((h, i) => { obj[h] = row[i]; });
    return obj;
  });
}

function decorateEntry_(e, projects) {
  const project = projects.find(p => p.id === e.projectId);
  return {
    id: e.id,
    projectId: e.projectId,
    projectName: project ? project.name : '(deleted project)',
    owner: project ? project.owner : '',
    clockIn: e.clockIn ? new Date(e.clockIn).toISOString() : null,
    clockOut: e.clockOut ? new Date(e.clockOut).toISOString() : null,
    hours: Number(e.hours || 0),
    notes: e.notes || '',
  };
}

function startOfWeek_(d) {
  const x = new Date(d.getFullYear(), d.getMonth(), d.getDate());
  const day = x.getDay();
  x.setDate(x.getDate() - day);
  return x;
}

function isAdmin_() {
  const email = (safeEmail_() || '').toLowerCase();
  const admins = (getSetting('adminEmails') || '')
    .split(',').map(s => s.trim().toLowerCase()).filter(Boolean);
  return admins.includes(email);
}

function round2_(n) { return Math.round(Number(n) * 100) / 100; }
