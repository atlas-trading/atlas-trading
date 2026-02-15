# UI/UX Guidelines for Atlas Trading Dashboard

## Language Policy

### CRITICAL: English Only
**ALL text in the admin dashboard MUST be in English.**

This includes:
- Page titles and headers
- Button labels
- Form labels and placeholders
- Error messages
- Success messages
- Tooltips and help text
- Chart labels and legends
- Table headers and content
- Any other user-facing text

**NO EXCEPTIONS.**

### Examples:
```typescript
// ✅ CORRECT
<h2>Trade Analysis</h2>
<button>Run Simulation</button>
<MetricItem label="Average Holding Time" value="24.5h" />

// ❌ WRONG
<h2>거래 분석</h2>
<button>시뮬레이션 실행</button>
<MetricItem label="평균 보유 시간" value="24.5h" />
```

---

## Emoji Policy

### CRITICAL: No Decorative Emojis
**Emojis are BANNED except for critical warnings.**

### Allowed:
- ⚠️ - **ONLY** for critical warnings, errors, or important alerts

### Forbidden:
- 📊 📈 📉 💰 💵 🔍 🎯 🔄 📋 🎲 - ALL decorative emojis
- ✓ ✗ - Even checkmarks are not allowed (use text instead)

### Examples:
```typescript
// ✅ CORRECT
<h2>Advanced Performance Metrics</h2>
<div>⚠️ High Tail Risk Dependency Detected</div>

// ❌ WRONG
<h2>📊 Advanced Performance Metrics</h2>
<div>✓ Good Profit Distribution</div>
```

---

## Date Format Policy

### CRITICAL: Numeric Date Format Only
**ALL dates MUST be in numeric format for quick readability.**

### Format Rules:
- **Short dates**: `M.D` (e.g., `12.1`, `3.15`)
- **Full dates**: `M.D.YYYY` (e.g., `12.1.2024`, `3.15.2025`)
- **Date-time**: `M.D.YYYY H:MM` (e.g., `12.1.2024 14:30`)

### Implementation:
```typescript
// ✅ CORRECT
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return `${date.getMonth() + 1}.${date.getDate()}.${date.getFullYear()}`;
};

const formatDateTime = (dateStr: string) => {
  const date = new Date(dateStr);
  return `${date.getMonth() + 1}.${date.getDate()}.${date.getFullYear()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
};

// For charts (short format)
const formatChartDate = (dateStr: string) => {
  const date = new Date(dateStr);
  return `${date.getMonth() + 1}.${date.getDate()}`;
};

// ❌ WRONG
new Date(dateStr).toLocaleDateString('ko-KR', { month: 'long', day: 'numeric' })
// Output: "12월 1일" ❌

new Date(dateStr).toLocaleDateString('en-US', { month: 'long', day: 'numeric' })
// Output: "December 1" ❌
```

### Why Numeric Format?
1. **Language-agnostic**: Works for all users regardless of locale
2. **Compact**: Saves space in tables and charts
3. **Scannable**: Easy to compare dates at a glance
4. **Professional**: Standard format in quantitative trading

---

## Checking Compliance

### Before Committing:
```bash
# Check for Korean text in TSX files
grep -r "[\uac00-\ud7a3]" src/

# Check for banned emojis
grep -r "[📊📈📉💰💵🔍🎯🔄📋🎲✓✗]" src/

# Check for locale-based date formatting
grep -r "toLocaleDateString" src/
```

### Common Violations:
1. **Korean text in error messages**
   - Fix: Replace with English equivalents

2. **Decorative emojis in headers**
   - Fix: Remove entirely (not even space)

3. **`toLocaleDateString('ko-KR')`**
   - Fix: Use numeric format function

---

## Enforcement

**These are NOT suggestions - they are MANDATORY rules.**

Any PR that violates these guidelines will be rejected immediately:
1. Korean text → **REJECTED**
2. Decorative emojis → **REJECTED**
3. Non-numeric date format → **REJECTED**

Only exception: The ⚠️ emoji for critical warnings.

---

## Rationale

### Why English Only?
- This is a **professional trading platform**
- Target audience: Institutional traders, quantitative analysts
- English is the **universal language of finance**
- Consistency across the entire admin interface

### Why No Emojis?
- Emojis are **unprofessional** in trading software
- They look **childish** and reduce credibility
- They add **visual noise** without value
- Only exception: ⚠️ draws attention to critical issues

### Why Numeric Dates?
- Trading professionals scan hundreds of dates daily
- `12.1` is **faster to read** than "December 1st" or "12월 1일"
- Compact format fits better in **tables and charts**
- Removes ambiguity (no "MM/DD vs DD/MM" confusion)

---

## Summary

1. **English only** - No Korean text anywhere
2. **⚠️ only** - No decorative emojis
3. **Numeric dates** - M.D.YYYY format

These rules ensure a professional, consistent, and efficient user interface.
