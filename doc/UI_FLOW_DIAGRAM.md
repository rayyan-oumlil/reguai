# Regulatory Document Analysis - UI Flow

## New Interface Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│  📊 Analyse de Documents et d'Impact Réglementaire                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  [📄 Analyse de Documents] [📈 Analyse d'Impact]                    │
│                                                                       │
├─────────────────────────────────────────────────────────────────────┤
│  📄 Analyse de Documents Réglementaires                             │
│  💡 Uploadez de nouveaux documents ou analysez les existants        │
│                                                                       │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │ 📤 Upload Nouveau Document                          [▼]      │   │
│  ├─────────────────────────────────────────────────────────────┤   │
│  │  [Choose File] document.html                                 │   │
│  │  ☑️ Utiliser AWS    ☑️ Utiliser cache                       │   │
│  │  [🔍 Analyser avec Bedrock]                                  │   │
│  └─────────────────────────────────────────────────────────────┘   │
│                                                                       │
│  ─────────────────────────────────────────────────────────────────  │
│                                                                       │
│  📚 Tous les Documents                                               │
│                                                                       │
│  Filtrer par statut: [Tous ▼]  ☐ Afficher documents masqués        │
│                                                                       │
│  📊 8 document(s) trouvé(s)                                          │
│                                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │ 📄 EU AI Act Regulation.html     📅 2024-11-01 14:30         │  │
│  │    432.5 KB                       ✅ Analysé                  │  │
│  │                                   [🗑️] [👁️‍🗨️]                │  │
│  │                                                                │  │
│  │  > 📋 Voir les résultats d'extraction                         │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ 📄 China Energy Law.html          📅 2024-10-28 09:15         │  │
│  │    856.2 KB                       ✅ Analysé                  │  │
│  │                                   [🗑️] [👁️‍🗨️]                │  │
│  ├──────────────────────────────────────────────────────────────┤  │
│  │ 📄 New Regulation.pdf             📅 2024-11-02 16:45         │  │
│  │    1.2 MB                         ⏳ Non analysé              │  │
│  │                                   [🔍] [👁️‍🗨️]                │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

## Action Buttons Explained

| Button | Status Required | Action | Result |
|--------|----------------|--------|--------|
| 🔍 | Not Analyzed | Analyze document with Bedrock | Extracts info, saves to cache |
| 🗑️ | Analyzed | Delete extraction result | Removes cached extraction |
| 👁️‍🗨️ | Any | Hide document | Hides from default view |
| 👁️ | Hidden | Show document | Shows in default view |

## User Workflows

### Workflow 1: Upload New Document
```
1. Click "📤 Upload Nouveau Document"
2. Choose file (HTML/XML/PDF/TXT)
3. Configure options (AWS, Cache)
4. Click "🔍 Analyser avec Bedrock"
5. Wait for extraction (1-3 minutes)
6. See suggested filename: "Title_Country_Date.ext"
7. View extraction results
8. Document appears in main list with ✅ Analysé status
```

### Workflow 2: Analyze Existing Document
```
1. Find document in "📚 Tous les Documents"
2. Document shows ⏳ Non analysé status
3. Click 🔍 button in actions column
4. Wait for extraction
5. Status changes to ✅ Analysé
6. Click expander to view results
```

### Workflow 3: Delete Extraction Result
```
1. Find analyzed document (✅ Analysé)
2. Click 🗑️ button in actions column
3. Extraction deleted immediately
4. Status changes to ⏳ Non analysé
5. Can re-analyze if needed
```

### Workflow 4: Hide/Show Documents
```
1. Find document you want to hide
2. Click 👁️‍🗨️ button
3. Document disappears from view
4. Check "☑️ Afficher documents masqués"
5. Hidden document appears with 👁️‍🗨️ icon
6. Click 👁️ to show again
```

### Workflow 5: Filter Documents
```
1. Use "Filtrer par statut" dropdown
   - Tous: Show all documents
   - Analysés: Show only analyzed documents
   - Non analysés: Show only pending documents
2. Toggle "Afficher documents masqués" checkbox
   - Checked: Show hidden documents
   - Unchecked: Hide hidden documents
```

## Data Flow Diagram

```
┌─────────────┐
│   Upload    │
│   File      │
└──────┬──────┘
       │
       ▼
┌─────────────────┐
│  Extract with   │
│  Bedrock        │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐     ┌──────────────┐
│  Generate       │────▶│  Suggested   │
│  Filename       │     │  Name        │
└──────┬──────────┘     └──────────────┘
       │
       ▼
┌─────────────────┐
│  Save to Cache  │
│  + Timestamp    │
└──────┬──────────┘
       │
       ▼
┌─────────────────┐
│  Display in     │
│  Unified View   │
└──────┬──────────┘
       │
       ▼
┌─────────────────────────────────┐
│  User Actions:                  │
│  • View Results (Expand)        │
│  • Delete Extraction (🗑️)       │
│  • Hide/Show (👁️)               │
│  • Re-analyze (🔍)              │
└─────────────────────────────────┘
```

## Status Indicators

### Document Status
- **✅ Analysé** (Green) - Document has been analyzed, results available
- **⏳ Non analysé** (Yellow) - Document exists but not yet analyzed

### Document Visibility
- **📄** - Normal document (visible)
- **👁️‍🗨️** - Hidden document (only visible when filter enabled)

### Cache Status
- **ℹ️ Résultats chargés depuis le cache** - Results loaded from cache (fast, no cost)
- **✅ Extraction terminée avec succès !** - New extraction completed (slower, uses API)

## Filter Combinations

| Filter Status | Show Hidden | Result |
|--------------|-------------|--------|
| Tous | ☐ | All visible documents |
| Tous | ☑️ | All documents including hidden |
| Analysés | ☐ | Only analyzed visible documents |
| Analysés | ☑️ | All analyzed documents including hidden |
| Non analysés | ☐ | Only non-analyzed visible documents |
| Non analysés | ☑️ | All non-analyzed documents including hidden |

## Benefits of New Design

### 1. **Less Navigation**
- Before: 3 tabs to navigate between
- After: 1 unified view with everything

### 2. **Faster Actions**
- Before: Expand → Scroll → Click button
- After: Click button directly

### 3. **Better Context**
- Before: Results separated from documents
- After: Results inline with documents

### 4. **More Control**
- Before: Can't delete or hide
- After: Full control with inline actions

### 5. **Better Information**
- Before: No upload date
- After: Upload date, size, status all visible

---

**Quick Reference:**
- 🔍 = Analyze
- 🗑️ = Delete extraction
- 👁️‍🗨️ = Hide
- 👁️ = Show
- ✅ = Analyzed
- ⏳ = Not analyzed
- 📄 = Document
- 📅 = Date

