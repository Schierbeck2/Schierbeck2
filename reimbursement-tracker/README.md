# Reimbursement Tracker

A small Google Apps Script web app for tracking your virtual assistant's hours
by project and computing what your coworker owes you.

## What it does

- **Assistant view** — your assistant signs in, sees the list of active projects,
  taps **Clock in** on whichever one she's starting. Switching projects auto-clocks
  her out of the previous one. She can edit or delete her own past entries.
- **Owner dashboard** — you see hour totals (week / month / YTD / all time) split
  between your projects and your coworker's, the running balance owed
  (`coworker hours × hourly rate − payments received`), and a payments log.
- **Monthly email** — on the 1st of each month at 8 a.m., a summary of the prior
  month's hours and the running balance is emailed to you.

All data lives in a single Google Sheet you own.

## One-time setup

1. **Create the Sheet.** In Google Drive, create a new Google Sheet. Name it
   anything (e.g. "Assistant Hours").
2. **Open the script editor.** From the Sheet, choose **Extensions → Apps Script**.
3. **Add the files.** Replace `Code.gs` and add HTML files to match this folder:
   - `Code.gs` → paste the contents of `Code.gs`
   - File → New → HTML, name it `Assistant` → paste `Assistant.html`
   - File → New → HTML, name it `Owner` → paste `Owner.html`
   - File → New → HTML, name it `Shared` → paste `Shared.html`
   - (Optional) Project Settings → "Show appsscript.json" → paste `appsscript.json`
4. **Initialize the Sheet tabs.** In the Apps Script editor, select the
   `ensureSheets_` function from the dropdown and click **Run**. Approve the
   permission prompts. This creates the `Settings`, `Projects`, `TimeEntries`,
   and `Payments` tabs and seeds default settings.
5. **Edit `Settings`.** Open the Sheet, go to the `Settings` tab, and confirm:
   - `hourlyRate` — the rate you'll charge your coworker per hour (e.g. `25`)
   - `adminEmails` — your Google account email (comma-separate to add more)
   - `coworkerName` — display name for your coworker
   - `summaryEmail` — where the monthly summary goes (defaults to yours)
6. **Add projects.** You can do this from the dashboard once deployed, or edit
   the `Projects` tab directly. Each project has an `owner` of either `You` or
   `Coworker`. The `id` can be any unique string — let the dashboard generate it.
7. **Deploy as a web app.** In the Apps Script editor: **Deploy → New deployment
   → Web app**.
   - Description: anything
   - Execute as: **Me**
   - Who has access: **Anyone with Google account** (so your assistant can sign in)
   - Click **Deploy** and copy the web app URL.
8. **Install the monthly email trigger.** In the editor, select
   `installMonthlyTrigger` and click **Run**. This schedules
   `sendMonthlySummary` to run on the 1st of each month at 8 a.m.

## Sharing with your assistant

Send her the web app URL from step 7. She'll need to sign in with a Google
account once. Anyone whose email is **not** in `adminEmails` automatically gets
the assistant view; you (and any other admin emails) get the dashboard.

If you ever want to look at the assistant view, append `?view=assistant` to the
URL. To force the dashboard for an admin, `?view=owner`.

## Data model

| Tab           | Columns                                                                |
|---------------|------------------------------------------------------------------------|
| `Settings`    | `key`, `value`                                                         |
| `Projects`    | `id`, `name`, `owner` (`You`/`Coworker`), `status` (`active`/`archived`) |
| `TimeEntries` | `id`, `projectId`, `assistantEmail`, `clockIn`, `clockOut`, `hours`, `notes` |
| `Payments`    | `id`, `date`, `amount`, `note`                                         |

You can edit anything directly in the Sheet if needed — the app reads on every
load.

## Updating

After editing files locally, re-paste them into the Apps Script editor and
**Deploy → Manage deployments → Edit (pencil) → Version: New version → Deploy**.
The same web app URL keeps working.
