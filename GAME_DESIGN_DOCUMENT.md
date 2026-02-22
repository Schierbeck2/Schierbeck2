# Manufactured Housing Community Kingpin
## Game Design Document v1.0

---

## 1. Game Overview

**Title:** Manufactured Housing Community Kingpin
**Genre:** Real Estate Tycoon / Business Strategy Simulation
**Platform:** Mobile (iOS & Android), potential Web PWA
**Perspective:** Top-down management with menu-driven decisions
**Session Length:** 10–30 minutes per play session
**Target Audience:** Strategy game fans, real estate enthusiasts, ages 16+

### 1.1 Elevator Pitch

You start with a small loan and a run-down mobile home park. Buy low, improve smart, manage residents, and grow your empire to 20 parks — increasing your portfolio value by 30% in just 5 years. Every month brings tough choices: fix the plumbing or buy another park? Raise rents or keep good tenants happy? One bad decision can tank your empire.

### 1.2 Win / Lose Conditions

| Outcome | Condition |
|---------|-----------|
| **Victory** | Own 20+ manufactured housing communities AND achieve 30%+ portfolio value increase before the end of Year 5 |
| **Bankruptcy Loss** | Cash balance drops below $0 with no available credit |
| **Regulatory Loss** | Accumulate 3+ unresolved code violations across your portfolio (parks get condemned) |
| **Reputation Loss** | Reputation score drops below 10 (no bank will lend, no seller will deal) |
| **Time Loss** | Year 5 ends without meeting the 20-park / 30%-growth targets |

### 1.3 Difficulty Modes

| Mode | Starting Cash | Loan Terms | Event Frequency | Market Volatility |
|------|--------------|------------|-----------------|-------------------|
| **Apprentice** | $500,000 | Favorable (4% interest) | Low | Mild |
| **Operator** | $250,000 | Standard (6% interest) | Medium | Moderate |
| **Kingpin** | $100,000 | Tough (8% interest) | High | Harsh |

---

## 2. Core Game Loop

The game runs on a **monthly tick** system. Each in-game month consists of these phases:

```
[INCOME PHASE] --> [EXPENSE PHASE] --> [EVENT PHASE] --> [DECISION PHASE] --> [MARKET PHASE] --> [END OF MONTH SUMMARY]
       |                                                                                                    |
       +----------------------------------------------------------------------------------------------------+
                                              NEXT MONTH
```

### 2.1 Income Phase (Automatic)
- Lot rent collected from occupied lots (adjusted for delinquency rate)
- Home rental income (if player owns rental units)
- Ancillary revenue: laundry facilities, storage, application fees
- Late fee income

### 2.2 Expense Phase (Automatic)
- Mortgage/loan payments (per park)
- Property taxes (quarterly)
- Insurance premiums (annual, spread monthly)
- Utility costs (water/sewer/electric — varies by park infrastructure)
- Payroll: on-site managers, maintenance staff
- Routine maintenance costs (scales with park age and condition)
- Legal/accounting fees

### 2.3 Event Phase (1–3 Events Per Month)
- Random events drawn from weighted event pools (see Section 7)
- Events require player response — ignore at your own risk
- Some events are park-specific, others are portfolio-wide

### 2.4 Decision Phase (Player-Driven)
Player can take actions across any owned park:
- Allocate capital improvement budget
- Adjust rent levels
- Hire/fire staff
- Approve/deny resident applications
- Respond to resident requests and complaints
- Begin eviction proceedings
- List vacant lots for marketing

### 2.5 Market Phase (Available Each Month)
- Browse available parks for sale
- Commission due diligence on prospective acquisitions
- Submit offers / negotiate deals
- Arrange financing
- Close on purchases

### 2.6 End of Month Summary
- Financial dashboard: revenue, expenses, NOI, cash position
- Park-by-park performance scorecards
- Portfolio valuation update
- Progress toward 20-park / 30%-value goals

---

## 3. Park Properties & Attributes

Each park in the game has the following attributes:

### 3.1 Fixed Attributes (Set at Acquisition)
| Attribute | Description | Example Range |
|-----------|-------------|---------------|
| **Name** | Park name | "Sunny Acres", "Whispering Pines" |
| **Location** | Region/market tier (A, B, C, D) | Affects rent ceiling, appreciation, event types |
| **Total Lots** | Number of home sites | 10 – 200 |
| **Year Built** | Age of infrastructure | 1955 – 2015 |
| **Zoning** | Current zoning designation | MH-Residential, Mixed Use, Agricultural |
| **Utilities** | City water/sewer vs. well/septic vs. private | Affects costs and risk |
| **Road Type** | Paved, gravel, dirt | Affects curb appeal and maintenance |

### 3.2 Dynamic Attributes (Change Over Time)
| Attribute | Description | Range |
|-----------|-------------|-------|
| **Occupancy Rate** | % of lots occupied | 0% – 100% |
| **Lot Rent** | Monthly rent per lot | $150 – $800 |
| **Condition Score** | Overall infrastructure health | 1 – 100 |
| **Curb Appeal** | Visual attractiveness | 1 – 100 |
| **Resident Satisfaction** | Average tenant happiness | 1 – 100 |
| **Code Compliance** | Regulatory standing | Compliant / Warning / Violation |
| **NOI** | Net Operating Income (monthly) | Calculated |
| **Valuation** | Current appraised value (NOI / Cap Rate) | Calculated |

### 3.3 Market Location Tiers

| Tier | Description | Avg Lot Rent | Cap Rate | Appreciation | Risk |
|------|-------------|-------------|----------|-------------|------|
| **A - Metro** | Major metro suburbs | $500–800 | 5–6% | High | Low vacancy, high price |
| **B - Secondary** | Mid-size cities | $350–500 | 6–7% | Moderate | Balanced |
| **C - Rural** | Small towns | $200–350 | 7–9% | Low | Higher vacancy risk |
| **D - Distressed** | Economically struggling areas | $150–250 | 9–12% | Very Low | High vacancy, high event risk |

---

## 4. Financial System (Deep Dive)

### 4.1 Revenue Streams

| Source | Description | Player Control |
|--------|-------------|----------------|
| **Lot Rent** | Monthly fee for occupying a lot | Set rent amount, raise frequency |
| **Home Rentals** | Rent from park-owned homes placed on lots | Buy/sell homes, set rental price |
| **Home Sales** | One-time profit from selling homes to residents | Negotiate sale price and terms |
| **Utilities Billing** | Submeter or flat-rate utility pass-through | Choose billing method |
| **Laundry** | Revenue from coin-op laundry facilities | Invest to build/upgrade |
| **Storage** | Monthly fees for storage units/lots | Build storage amenities |
| **Application Fees** | Fee charged per new resident application | Set fee amount |
| **Late Fees** | Penalties for late rent payment | Set policy |

### 4.2 Expense Categories

| Category | Description | Player Control |
|----------|-------------|----------------|
| **Debt Service** | Monthly mortgage/loan payments | Choose financing terms at purchase |
| **Property Tax** | Local tax based on assessed value | Appeal assessments (event) |
| **Insurance** | Property + liability coverage | Choose coverage level |
| **Payroll** | Managers ($3–5K/mo), Maintenance ($2–4K/mo) | Hire/fire, set staffing levels |
| **Maintenance** | Routine repairs, mowing, snow removal | Budget allocation |
| **Capital Improvements** | Roads, utilities, amenities, landscaping | Budget allocation |
| **Utilities** | Water/sewer/electric (if not billed back) | Infrastructure upgrades reduce cost |
| **Legal** | Evictions, compliance, contracts | Decisions trigger costs |
| **Marketing** | Advertising vacant lots | Budget allocation |
| **Admin** | Accounting, software, supplies | Scales with portfolio size |

### 4.3 Valuation Mechanics

Parks are valued using the **Income Approach** (realistic to the industry):

```
Park Value = Annual NOI / Capitalization Rate

NOI = (Annual Revenue) - (Annual Operating Expenses)
     (excludes debt service)

Cap Rate = determined by market tier, park condition, and occupancy
```

**Example:**
- Annual Lot Rent Revenue: $360,000 (100 lots x $300/mo)
- Annual Operating Expenses: $144,000 (40% expense ratio)
- NOI: $216,000
- Cap Rate: 8%
- Park Value: $216,000 / 0.08 = **$2,700,000**

**How the player increases value:**
1. Raise lot rents (increases revenue)
2. Fill vacant lots (increases revenue)
3. Reduce expenses via infrastructure upgrades (increases NOI)
4. Improve condition/location tier (lowers cap rate = higher value)
5. Add revenue streams (laundry, storage, home sales)

### 4.4 Financing Options

| Type | Down Payment | Interest | Term | Pros | Cons |
|------|-------------|----------|------|------|------|
| **Bank Loan** | 25% | 5–7% | 20 yr | Lowest rate | Slow approval, strict requirements |
| **Seller Financing** | 10–20% | 7–10% | 5–10 yr | Fast, flexible | Higher rate, balloon payment risk |
| **Private Investor** | 0–10% | 10–15% | 3–5 yr | Quick cash, no bank needed | Expensive, investor may want control |
| **Cash Purchase** | 100% | 0% | N/A | No debt, max cash flow | Ties up all capital |
| **Portfolio Line of Credit** | N/A | 6–8% | Revolving | Flexible, quick draws | Based on portfolio equity, variable rate |

---

## 5. Resident System

Residents are the lifeblood of the business. Each occupied lot has a resident profile.

### 5.1 Resident Attributes

| Attribute | Description | Range |
|-----------|-------------|-------|
| **Name** | Generated resident name | — |
| **Tenure** | Months in the park | 0+ |
| **Payment Reliability** | Likelihood of paying on time | 1–100 |
| **Home Condition** | Upkeep of their home | 1–100 (affects curb appeal) |
| **Satisfaction** | How happy they are | 1–100 |
| **Compliance** | Rule-following tendency | 1–100 |
| **Income Level** | Affects rent tolerance | Low / Medium / High |

### 5.2 Resident Satisfaction Drivers

| Factor | Impact | Player Lever |
|--------|--------|-------------|
| Rent affordability | High | Set rent levels, limit increase frequency |
| Maintenance responsiveness | High | Budget for maintenance staff and repairs |
| Park condition / curb appeal | Medium | Capital improvements, landscaping |
| Community amenities | Medium | Build playground, clubhouse, pool |
| Noise / neighbor issues | Medium | Enforce rules, mediate disputes |
| Management professionalism | Medium | Hire quality managers |
| Sense of community | Low–Medium | Host events (BBQs, holiday parties) |
| Recent rent increase | Negative | Frequency and size of increases |

### 5.3 Resident Actions & Consequences

| Scenario | Options | Consequence |
|----------|---------|-------------|
| **Late on rent (1st time)** | Waive late fee / Charge late fee / Issue warning | Satisfaction +/- , Revenue +/- |
| **Late on rent (3rd time)** | Payment plan / Begin eviction / Final warning | Risk of vacancy vs. continued delinquency |
| **Home in disrepair** | Send violation notice / Offer repair assistance / Ignore | Curb appeal, code compliance |
| **Noise complaint** | Mediate / Warn offender / Ignore | Satisfaction of surrounding residents |
| **Requests improvement** | Approve (spend $) / Deny / Compromise | Satisfaction, retention |
| **Wants to move out** | Offer incentive to stay / Let them go | Vacancy cost vs. retention cost |
| **Long-term great tenant** | Reward (rent discount, gift) / Do nothing | Loyalty, word-of-mouth referrals |

### 5.4 Turnover Economics

Losing a resident is expensive. The game models this realistically:

| Cost | Amount |
|------|--------|
| Lost rent during vacancy | $300–800/mo x avg 2–4 months |
| Lot cleanup / prep | $500–2,000 |
| Marketing to fill lot | $200–500 |
| New home move-in coordination | $500–1,000 |
| **Total turnover cost** | **$1,500–6,000+ per lot** |

This creates meaningful tension: raising rents boosts revenue but risks turnover.

---

## 6. Staffing & Operations

### 6.1 Staff Roles

| Role | Monthly Cost | Effect | Required At |
|------|-------------|--------|-------------|
| **On-Site Manager** | $3,000–5,000 | Handles day-to-day, +15 resident satisfaction, reduces event severity | 1 per park (>30 lots) |
| **Maintenance Tech** | $2,500–4,000 | Faster repairs, +10 condition score per month | 1 per 50 lots |
| **Groundskeeper** | $2,000–3,000 | +10 curb appeal, mowing/landscaping | Optional, high ROI on curb appeal |
| **Regional Manager** | $6,000–8,000 | Manages up to 5 parks remotely, +5% efficiency | Unlocked at 5+ parks |
| **Bookkeeper** | $2,000–3,000 | Reduces admin costs by 20%, early warning on financial issues | Optional |

### 6.2 Staff Quality

Staff hired from a pool with quality ratings (1–5 stars):
- Higher quality = higher salary demand
- Low-quality staff can cause problems (mishandle residents, miss maintenance)
- Staff can quit if overworked (too many lots per person)
- Training option: spend money to increase staff quality over time

---

## 7. Event System (Deep Dive)

Events are the "spice" of the game. They prevent passive play and force interesting decisions.

### 7.1 Event Categories

#### Weather & Natural Disasters
| Event | Probability | Impact | Player Response Options |
|-------|------------|--------|------------------------|
| **Severe Storm** | 5%/month (seasonal) | Roof damage to 5–15% of homes, tree debris | File insurance claim / Pay out of pocket / Ignore (condition drops) |
| **Tornado** | 1%/month (seasonal) | Major damage to 1–3 homes, infrastructure damage | Insurance + FEMA aid / Emergency repairs / Relocate residents |
| **Flooding** | 3%/month (seasonal) | Water damage, lot erosion, sewer backup | Emergency pumping / Insurance claim / Infrastructure upgrade |
| **Winter Storm** | 8%/month (winter) | Pipe bursts, road damage, snow removal costs | Pre-season prep reduces impact / Emergency response |
| **Drought** | 2%/month (summer) | Water restrictions, well issues, fire risk | Water conservation program / Well drilling |

#### Regulatory & Government
| Event | Probability | Impact | Player Response Options |
|-------|------------|--------|------------------------|
| **Code Inspection** | 10%/month | Inspector finds violations if condition < 60 | Fix immediately ($$) / Request extension / Contest findings |
| **Rent Control Ordinance** | 2%/year | Caps annual rent increases at 3–5% | Lobby against ($$) / Comply / Shift strategy to other revenue |
| **Zoning Change Proposal** | 1%/year | Could restrict expansion or enable rezoning | Attend hearings / Hire lobbyist / Adapt |
| **Tax Reassessment** | 1%/year | Property tax increase 10–25% | Appeal assessment / Budget for increase |
| **Environmental Issue** | 2%/year | Contamination found on site | Remediation ($$$) / Sell park / Negotiate with EPA |
| **ADA Compliance Notice** | 3%/year | Accessibility upgrades required | Comply ($$) / Request waiver |

#### Resident Events
| Event | Probability | Impact | Player Response Options |
|-------|------------|--------|------------------------|
| **Rent Strike** | 1–3%/month (if satisfaction < 30) | Group of residents refuse to pay | Negotiate / Evict leaders / Address grievances |
| **Community Petition** | 5%/month | Residents request improvement | Fund request / Partial compromise / Deny |
| **Resident Dispute** | 10%/month | Neighbor conflict | Mediate / Warn both / Evict aggressor |
| **Unauthorized Occupant** | 5%/month | Extra person living in home unreported | Add to lease / Issue violation / Ignore |
| **Home Abandonment** | 3%/month | Resident leaves without notice | Clean up lot / Sell abandoned home / Legal process |
| **Local Hero** | 2%/month | Resident does something great for community | Recognize publicly (+satisfaction) / Do nothing |

#### Market & Economic
| Event | Probability | Impact | Player Response Options |
|-------|------------|--------|------------------------|
| **Interest Rate Hike** | 5%/quarter | Variable loan payments increase | Refinance / Absorb cost / Accelerate payoff |
| **Housing Market Boom** | 5%/year | Park values increase, but so do acquisition costs | Sell a park for profit / Hold / Buy before prices rise more |
| **Recession** | 3%/year | Occupancy may increase (affordable housing demand) but payment reliability drops | Tighten screening / Offer payment plans / Raise rents cautiously |
| **New Competitor** | 3%/year | New MHC opens nearby, draws residents | Improve amenities / Lower rents / Marketing push |
| **Bulk Home Deal** | 5%/year | Dealer offers 10+ homes at discount | Buy and place on lots / Pass |
| **Investor Buyout Offer** | 2%/year | Investor offers to buy one of your parks | Sell (quick cash) / Counter-offer / Decline |

#### Operations & Staff
| Event | Probability | Impact | Player Response Options |
|-------|------------|--------|------------------------|
| **Manager Quits** | 3%/month | Park runs unmanaged, satisfaction drops | Hire replacement / Promote from within / Manage remotely |
| **Maintenance Emergency** | 8%/month | Sewer line break, electrical fire, water main burst | Emergency repair ($$) / Temporary fix ($) / Ignore (violation risk) |
| **Vandalism** | 5%/month | Property damage to common areas | Police report + repair / Increase security / Ignore |
| **Lawsuit Filed** | 2%/month | Slip-and-fall, discrimination, wrongful eviction | Settle ($) / Fight in court ($$+time) / Mediate |

### 7.2 Event Weighting

Events are weighted by:
- **Park condition** — Low condition parks get more maintenance emergencies and code violations
- **Occupancy** — High occupancy = more resident events, low occupancy = more financial pressure
- **Location tier** — D-tier parks get more crime/vandalism, A-tier get more regulatory events
- **Season** — Weather events are seasonal
- **Portfolio size** — More parks = higher chance of at least one event per month
- **Reputation** — Low reputation triggers more inspections and lawsuits

---

## 8. Upgrade & Improvement System

### 8.1 Infrastructure Upgrades

| Upgrade | Cost | Time | Effect |
|---------|------|------|--------|
| **Repave Roads** | $2,000–5,000/lot | 2 months | +20 condition, +15 curb appeal, lower maintenance |
| **Replace Water Lines** | $3,000–6,000/lot | 3 months | -30% water-related emergencies, +15 condition |
| **Upgrade Sewer System** | $4,000–8,000/lot | 4 months | -40% sewer emergencies, code compliance |
| **Electrical Upgrade** | $1,500–3,000/lot | 2 months | -20% electrical emergencies, supports new homes |
| **Install Submeters** | $500–800/lot | 1 month | Utility costs shift to residents, +15% NOI |
| **Storm Drainage** | $1,000–2,000/lot | 2 months | -50% flood damage |
| **Perimeter Fencing** | $500–1,000/lot | 1 month | -30% vandalism, +5 curb appeal |

### 8.2 Amenity Additions

| Amenity | Cost | Monthly Upkeep | Effect |
|---------|------|---------------|--------|
| **Playground** | $15,000–30,000 | $200 | +10 satisfaction, attracts families |
| **Clubhouse** | $50,000–100,000 | $500 | +15 satisfaction, enables community events |
| **Laundry Facility** | $25,000–40,000 | $300 | +$500–1,500/mo revenue, +5 satisfaction |
| **Dog Park** | $10,000–20,000 | $150 | +8 satisfaction, reduces pet complaints |
| **Swimming Pool** | $40,000–80,000 | $800 | +20 satisfaction, major draw — but liability risk |
| **Community Garden** | $5,000–10,000 | $100 | +7 satisfaction, good PR |
| **Security Cameras** | $10,000–20,000 | $200 | -25% vandalism/crime events, +5 satisfaction |
| **RV/Boat Storage** | $20,000–40,000 | $200 | +$1,000–3,000/mo revenue |
| **Wi-Fi Common Areas** | $5,000–10,000 | $300 | +5 satisfaction, modern appeal |

### 8.3 Cosmetic Upgrades

| Upgrade | Cost | Effect |
|---------|------|--------|
| **New Park Signage** | $2,000–8,000 | +10 curb appeal |
| **Landscaping Package** | $5,000–15,000 | +15 curb appeal, +5 satisfaction |
| **Street Lighting** | $8,000–15,000 | +8 curb appeal, -15% crime events |
| **Mailbox Stations** | $3,000–6,000 | +5 curb appeal |
| **Welcome Center** | $20,000–40,000 | +10 curb appeal, +10% application rate |

---

## 9. Acquisition & Due Diligence

### 9.1 Market Listings

Each month, 2–5 parks appear on the market. Listings show:
- Asking price
- Location tier
- Total lots and occupancy (may be inaccurate — verify in due diligence)
- Headline description ("Well-maintained 60-lot park" or "Fixer-upper, motivated seller")
- Seller type icon (bank/estate/mom-and-pop/investor)

### 9.2 Due Diligence Mini-Game

Before buying, the player pays $2,000–10,000 for due diligence. This reveals:

| Inspection Area | Cost | What It Reveals |
|-----------------|------|-----------------|
| **Physical Inspection** | $3,000–5,000 | True condition score, hidden infrastructure issues |
| **Financial Audit** | $2,000–3,000 | Actual income/expense records, rent roll accuracy |
| **Environmental Phase I** | $2,000–4,000 | Contamination risk (skip at your peril) |
| **Title Search** | $1,000–2,000 | Liens, easements, legal encumbrances |
| **Market Analysis** | $1,500–2,500 | Local rent comps, demand trends, competition |

**Risk/Reward:** Skipping due diligence saves money but can result in nasty surprises — hidden environmental contamination, inflated rent rolls, or structural issues that cost 10x what the inspection would have.

### 9.3 Negotiation

Simple negotiation mechanic:
1. See asking price
2. Submit offer (% of asking)
3. Seller counters based on: market conditions, their motivation level, how long the listing has been available
4. Accept / Counter / Walk away
5. Motivated sellers (estate sales, tired landlords) accept lower offers
6. Hot markets mean less room to negotiate

---

## 10. Progression & Milestones

### 10.1 Achievement System

| Achievement | Condition | Reward |
|-------------|-----------|--------|
| **First Keys** | Acquire your first park | Tutorial bonus: $10,000 |
| **Fixer Upper** | Increase a park's condition by 50 points | Unlock contractor discount (10% off improvements) |
| **Full House** | Reach 100% occupancy on any park | Marketing boost: +20% application rate |
| **Five Alive** | Own 5 parks simultaneously | Unlock Regional Manager hiring |
| **Cash Cow** | Have a single park generate $20K+ NOI/month | Unlock Portfolio Line of Credit |
| **People Person** | Maintain 80+ satisfaction across all parks for 6 months | Turnover rate -25% |
| **Negotiator** | Purchase a park for 20%+ below asking | Unlock "Lowball" negotiation option |
| **Survivor** | Successfully handle a natural disaster | Insurance premium discount 10% |
| **The Dozen** | Own 12 parks | Unlock bulk purchasing discounts |
| **Empire Builder** | Own 20 parks | Prerequisite for victory |
| **Kingpin** | Win the game (20 parks + 30% value increase) | Final victory screen + stats |

### 10.2 Quarterly Reports

Every 3 in-game months, the player receives a detailed quarterly report:
- Portfolio value trend graph
- Park-by-park performance ranking
- Cash flow summary
- Progress toward 20-park goal (visual tracker)
- Progress toward 30% value goal (visual tracker)
- Letter grade (A–F) for overall performance
- "Investor Confidence" score that affects loan availability

### 10.3 Year-End Review

Annual summary with:
- Year-over-year comparison
- Best and worst performing parks
- Total return on investment
- Market outlook for next year
- Unlocked achievements
- Difficulty adjustment suggestion (if struggling or dominating)

---

## 11. UI / UX Design

### 11.1 Main Screens

```
+--------------------------------------------------+
|  PORTFOLIO DASHBOARD (Home Screen)                |
|  +---------+ +---------+ +---------+              |
|  | Park 1  | | Park 2  | | Park 3  |  ...        |
|  | Sunny   | | Pine    | | Oak     |              |
|  | Acres   | | Valley  | | Ridge   |              |
|  | 92% Occ | | 78% Occ | | 45% Occ |              |
|  | $12K NOI| | $8K NOI | | $3K NOI |              |
|  |   [OK]  | |  [WARN] | |  [!!!]  |              |
|  +---------+ +---------+ +---------+              |
|                                                    |
|  Cash: $145,000    Debt: $2.1M    NOI: $23K/mo    |
|  Portfolio Value: $3.8M  (+12% from start)         |
|  Parks: 3/20            Year 1, Month 8            |
|                                                    |
|  [NEXT MONTH]  [MARKET]  [FINANCES]  [SETTINGS]   |
+--------------------------------------------------+
```

```
+--------------------------------------------------+
|  PARK DETAIL SCREEN                               |
|  Sunny Acres MHC          Location: B-Market      |
|  ----------------------------------------         |
|  Lots: 60 total | 55 occupied (92%)               |
|  Lot Rent: $325/mo                                |
|  Condition: 72/100  |  Curb Appeal: 65/100        |
|  Satisfaction: 78/100                              |
|  Monthly NOI: $12,400                              |
|  Valuation: $1,860,000                             |
|  ----------------------------------------         |
|  Staff: Manager (4-star), Maintenance (3-star)     |
|  ----------------------------------------         |
|  [RESIDENTS]  [UPGRADES]  [FINANCES]  [STAFF]     |
|  [SET RENT]   [MARKETING] [INSPECT]               |
+--------------------------------------------------+
```

```
+--------------------------------------------------+
|  EVENT POPUP                                       |
|  ==========================================        |
|  PIPE BURST at Sunny Acres!                       |
|  ==========================================        |
|  A major water line has burst on Lot 34.           |
|  Water is flooding the road. 6 homes have         |
|  reduced water pressure.                           |
|                                                    |
|  Estimated repair: $4,500                          |
|  If ignored: -15 condition, -20 satisfaction,      |
|  risk of code violation                            |
|                                                    |
|  [Emergency Repair - $4,500]                       |
|  [Temporary Patch - $800]  (may fail again)        |
|  [Ignore for Now]  (consequences likely)           |
+--------------------------------------------------+
```

```
+--------------------------------------------------+
|  MARKET / ACQUISITION SCREEN                      |
|  Parks for Sale This Month:                        |
|  +---------+---------+---------+---------+        |
|  | Willow  | Cedar   | Maple   | Elm     |        |
|  | Creek   | Heights | Estates | Court   |        |
|  | 80 lots | 40 lots | 120 lots| 25 lots |        |
|  | 65% occ | 90% occ | 50% occ | 88% occ|        |
|  | C-Mkt   | A-Mkt   | D-Mkt   | B-Mkt  |        |
|  | $1.2M   | $2.8M   | $800K   | $680K  |        |
|  |[Details]|[Details]|[Details]|[Details] |        |
|  +---------+---------+---------+---------+        |
|                                                    |
|  Your Cash: $145,000                               |
|  Available Credit: $500,000                        |
|  [FILTER]  [SORT]  [REFRESH]                       |
+--------------------------------------------------+
```

### 11.2 Navigation Flow

```
Portfolio Dashboard
  |
  +-- Park Detail
  |     +-- Residents List --> Resident Detail
  |     +-- Upgrades Menu --> Confirm Purchase
  |     +-- Park Finances --> Income/Expense Breakdown
  |     +-- Staff Management --> Hire/Fire/Train
  |     +-- Set Rent --> Rent Adjustment Screen
  |     +-- Marketing --> Ad Campaign Setup
  |
  +-- Market
  |     +-- Park Listing --> Due Diligence --> Offer --> Negotiation --> Closing
  |
  +-- Portfolio Finances
  |     +-- Cash Flow Statement
  |     +-- Balance Sheet
  |     +-- Loan Summary
  |     +-- Valuation Breakdown
  |
  +-- Events Queue (if pending events)
  |
  +-- Next Month (advance time)
  |
  +-- Settings / Save / Load
```

### 11.3 Visual Style Direction
- Clean, modern flat design with a business/professional feel
- Color palette: Deep greens (money/growth), warm golds (success), alert reds
- Iconography: Simple line icons for park features, staff, amenities
- Satisfying animations for: closing deals, rent coming in, upgrades completing
- Data visualization: sparkline charts, progress bars, color-coded health indicators

---

## 12. Audio Design

| Context | Sound |
|---------|-------|
| Monthly rent collection | Cash register "cha-ching" |
| Event notification | Alert chime (urgency varies) |
| Deal closed (acquisition) | Gavel slam + applause |
| Upgrade completed | Construction finish jingle |
| Negative event | Low tension note |
| Bankruptcy approaching | Ominous tone |
| Victory screen | Triumphant fanfare |
| Background music | Chill lo-fi business beats (toggleable) |

---

## 13. Tutorial & Onboarding

### 13.1 Guided First Park

The first 3 in-game months are a tutorial:

**Month 1: "The Keys"**
- Player receives their first park (small, 30-lot, C-market, 60% occupancy)
- Guided tour of the dashboard and park detail screens
- Explains lot rent, occupancy, condition scores

**Month 2: "The Basics"**
- First event triggers (simple maintenance issue)
- Teaches event response system
- Introduces the financial summary

**Month 3: "Growing Up"**
- Market opens — player can browse their first potential acquisition
- Teaches due diligence and negotiation
- Introduces the upgrade system
- Tutorial ends — "You're on your own now, Kingpin."

### 13.2 Tooltips & Help

- Every number on screen has a tap-to-explain tooltip
- "Advisor" character offers optional tips during the first year
- In-game glossary of real estate terms (NOI, cap rate, etc.)

---

## 14. Monetization Strategy (If Applicable)

### Option A: Premium (Recommended for quality feel)
- One-time purchase: $4.99–$9.99
- No ads, no in-app purchases
- All content included

### Option B: Free-to-Play with Ethical Monetization
- Free base game with ads between months (skippable after 5 sec)
- $3.99 to remove ads permanently
- Optional cosmetic packs: park themes, custom signage styles
- NO pay-to-win mechanics (no buying in-game cash)

### Option C: Freemium with Expansion Packs
- Free base game (limited to 5 parks, 2-year timeline)
- Full game unlock: $4.99
- Expansion packs ($1.99 each):
  - "Hurricane Alley" — Coastal markets with extreme weather
  - "Oil Country" — Boom/bust economic events
  - "Senior Living" — 55+ communities with different mechanics
  - "Resort Living" — Seasonal/vacation MHCs

---

## 15. Replayability

| Feature | Description |
|---------|-------------|
| **Procedural Generation** | Park attributes, events, and market conditions are randomized each playthrough |
| **Multiple Strategies** | Win via value-add turnarounds, cash flow stacking, or aggressive growth |
| **Difficulty Modes** | 3 difficulty levels offer different experiences |
| **Achievements** | 20+ achievements encourage different playstyles |
| **Leaderboard** | Score based on: final portfolio value, time to win, parks owned, resident satisfaction |
| **Scenario Mode** | Pre-built challenges: "Turn around this bankrupt park," "Survive the recession," etc. |
| **Endless Mode** | No win condition — just keep growing and optimizing forever |

---

## 16. Future Feature Ideas (Post-Launch)

- **Multiplayer** — Compete for parks in the same market with other players
- **Story Mode** — Narrative campaign with characters, rivals, and plot twists
- **Real Market Data** — Use actual MHC market data for realistic scenarios
- **Park Designer** — Visual lot layout editor
- **Social Features** — Share portfolio screenshots, compare stats with friends
- **Seasonal Events** — Holiday-themed in-game events
- **Community Challenges** — Weekly/monthly global challenges

---

## Appendix A: Glossary

| Term | Definition |
|------|-----------|
| **MHC** | Manufactured Housing Community (mobile home park) |
| **NOI** | Net Operating Income — Revenue minus operating expenses |
| **Cap Rate** | Capitalization Rate — NOI / Property Value (used for valuation) |
| **Lot Rent** | Monthly fee a resident pays for their home site |
| **Occupancy Rate** | Percentage of lots with paying residents |
| **Debt Service** | Monthly loan/mortgage payments |
| **Expense Ratio** | Operating expenses as a percentage of revenue |
| **Curb Appeal** | Visual attractiveness of the park |
| **Due Diligence** | Investigation before purchasing a property |
| **Seller Financing** | Seller acts as the bank, buyer pays over time |
| **Balloon Payment** | Large lump-sum payment due at end of a loan term |
| **Submetering** | Individual utility meters for each lot |

---

*Document Version: 1.0*
*Last Updated: February 2026*
*Status: Design Phase*
