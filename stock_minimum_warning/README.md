# Stock Minimum Warning

**Version:** 18.0.1.0.0
**Author:** TwenTIC
**Depends:** `sale_stock`
**License:** LGPL-3

---

## What this module adds to the Odoo circuit

### Overview

The standard Odoo `sale_stock` module already displays a small chart icon (🗠) on each sale order line indicating whether enough stock is forecasted for the delivery date. The icon turns **red** when there is a shortage.

**Stock Minimum Warning** extends this widget to bring two additional pieces of intelligence into the day-to-day sales workflow:

1. **Visibility of competing demand** – shows how much of a product is already sitting in *other* unconfirmed quotations (state `draft` or `sent`), so the salesperson can immediately see whether their apparent "green" stock is in fact already being counted on by colleagues.

2. **Proactive notification** – when a quotation is confirmed and that confirmation causes the forecasted stock of another quotation to go negative, the salesperson responsible for that other quotation is automatically alerted.

---

## Functional description

### 1. Widget colour logic

| Icon colour | Meaning |
|---|---|
| **Red** (`text-danger`) | Forecasted stock at delivery date is already insufficient (existing Odoo behaviour). |
| **Yellow** (`text-warning`) *(new)* | Forecasted stock is positive, but after subtracting the quantities already included in other unconfirmed quotations, the net available quantity drops to zero or below. |
| *No colour / default* | Sufficient stock even after accounting for competing quotations. |

> The yellow state is a **soft warning**: stock exists on paper, but it is being claimed by quotations that have not yet been confirmed. Whoever confirms first wins the stock.

### 2. Extended popover (click on the icon)

Clicking the icon opens the standard availability popover, which now contains an extra section for lines in **draft or sent** state:

| Field | Description |
|---|---|
| Forecasted Stock | Stock forecasted at the delivery date (existing). |
| Available | Current stock including all planned operations (existing). |
| **In Unconfirmed Quotations** *(new)* | Total quantity of this product present in other quotations that have not yet been confirmed. Displayed in yellow when non-zero. |

A new **"View Draft Quotations"** button opens a list of all draft/sent sale orders that contain the same product, so the salesperson can review who else is competing for the same stock before deciding to confirm.

### 3. Automatic notification on confirmation

When a sale order is confirmed (`Confirm Order`), the module:

1. Identifies all other draft/sent quotations that contain at least one product from the confirmed order.
2. Recomputes the forecasted stock for those quotation lines (reflecting the new stock moves created by the confirmation).
3. For each affected quotation whose forecasted stock has turned negative:
   - Posts an **internal note** on the quotation's chatter describing which confirmed order caused the issue.
   - Schedules a **Warning activity** assigned to the quotation's salesperson so the alert surfaces in their activity list.

Only one notification per affected quotation is sent per confirmation event (no duplicate messages).

---

## Circuit impact diagram

```
Salesperson A creates Quotation Q1 (product X, qty 10)
Salesperson B creates Quotation Q2 (product X, qty 8)

Stock on hand: 10 units

Quotation Q1 widget icon:
  → Yellow ⚠️  (10 forecasted - 8 in Q2 = 2 net, but Q2 claims 8 so Q1 is at risk)

Salesperson A clicks icon:
  → Popover shows: Forecasted 10 | Available 10 | In Unconfirmed Quotations: 8
  → Button "View Draft Quotations" → opens Q2 in list view

Salesperson B confirms Q2:
  → Stock moves created, forecasted stock for Q1 product X drops below 0
  → Internal note posted on Q1: "⚠️ Q2 confirmed, stock may be insufficient"
  → Warning activity created for Salesperson A on Q1
```

---

## User manual

### Installation

1. Copy the `stock_minimum_warning` folder into your Odoo addons path.
2. Update the module list (Settings → Technical → Update Module List or restart with `-u all`).
3. Install **Stock Minimum Warning** from the Apps menu.
4. No additional configuration is required.

### Viewing stock warnings on a quotation

1. Open any sale quotation (state **Quotation** or **Quotation Sent**).
2. In the order lines, locate the **🗠** (chart) icon in the rightmost column of each line.
3. **Icon colours:**
   - *No colour* – stock is sufficient.
   - **Yellow** – stock exists, but other quotations are already using it. Act quickly or source more.
   - **Red** – stock is already insufficient even before accounting for competing quotations.
4. **Click the icon** to open the availability popover:
   - Review the **Forecasted Stock** and **Available** quantities.
   - Check the **In Unconfirmed Quotations** row (shown in yellow) to see how much competing demand exists.
   - Click **"View Draft Quotations"** to open the list of competing quotations for that product.

### Reviewing competing quotations

1. From the popover, click **"View Draft Quotations"**.
2. A list view of all draft/sent quotations containing the same product opens.
3. You can open each quotation to assess priority, negotiate with colleagues, or decide to source additional stock.

### Handling stock shortage notifications

1. When a colleague confirms a sale order that uses stock you were counting on, you will receive:
   - A **Warning activity** in your activity list (bell icon / Activities menu). Click it to open the affected quotation.
   - An **internal note** in the affected quotation's chatter explaining which confirmed order caused the issue.
2. Open the quotation, review the impacted product lines (the icon will now be **red**), and take one of these actions:
   - Adjust the quantity.
   - Change the delivery date to when new stock is expected.
   - Trigger a replenishment from the stock forecast view (click **"View Forecast"** in the popover).
   - Communicate with the customer about a potential delay.
3. Mark the activity as **Done** once you have resolved the situation.

### Field reference

| Model | Field | Description |
|---|---|---|
| `sale.order.line` | `qty_in_draft_quotations` | Float – total qty of this product in other draft/sent quotations (computed, not stored). |
| `sale.order.line` | `draft_quotation_warning` | Boolean – True when `virtual_available_at_date > 0` but `virtual_available_at_date − qty_in_draft_quotations ≤ 0` (computed, not stored). |

---

## Technical notes

- Both new fields are **non-stored computed fields**, meaning they are always computed fresh from the database at access time. No manual recomputation is needed.
- The batch computation groups lines by their parent order to minimise the number of SQL queries.
- The JS widget is extended via Odoo's `patch()` utility, targeting `QtyAtDateWidget` and `QtyAtDatePopover` from `@sale_stock/widgets/qty_at_date_widget`. No core files are modified.
- OWL template inheritance (`t-inherit`) is used to inject new rows and buttons into the existing popover without replacing it.
- The notification system invalidates the ORM cache for `virtual_available_at_date` after each confirmation to ensure fresh forecasted data is used in the stock check.
