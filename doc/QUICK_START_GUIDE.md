# 🚀 Quick Start Guide - New Regulatory Document Analysis

## 📋 What's New?

The regulatory document analysis interface has been completely redesigned with:
- ✅ Auto-rename based on document content
- ✅ Delete individual extraction results
- ✅ Hide/show documents
- ✅ Upload date tracking
- ✅ Unified view with inline actions
- ✅ Smart filtering

## 🏃 Getting Started (2 Minutes)

### 1. Launch the App
```bash
cd /Users/rayanelgouri/Documents/Dev/ReguAI
source venv/bin/activate
streamlit run scripts/app.py
```

### 2. Navigate to Document Analysis
- Click **"📊 Analyse"** in the sidebar
- Click **"📄 Analyse de Documents"** tab

### 3. You'll See:
```
📤 Upload Nouveau Document (collapsed)
📚 Tous les Documents (main view)
```

## 🎯 Common Tasks

### Task 1: Upload & Analyze a New Document (30 seconds)

1. **Click** "📤 Upload Nouveau Document"
2. **Choose** your file (HTML, XML, PDF, or TXT)
3. **Click** "🔍 Analyser avec Bedrock"
4. **Wait** 1-3 minutes for extraction
5. **See** suggested filename (e.g., `EU_AI_Act_European_Union_2024-07-12.html`)
6. **View** results inline
7. **Find** document in list below with ✅ status

**Done!** Document is now in your library.

---

### Task 2: Analyze an Existing Document (10 seconds)

1. **Find** document in "📚 Tous les Documents"
2. **Look** for ⏳ (not analyzed) status
3. **Click** 🔍 button in the actions column
4. **Wait** for extraction
5. **Click** expander to view results

**Done!** Status changes to ✅.

---

### Task 3: View Extraction Results (5 seconds)

1. **Find** document with ✅ status
2. **Click** "📋 Voir les résultats d'extraction"
3. **Read** extracted information:
   - Category & confidence
   - Title, country, date
   - Affected sectors
   - Key requirements
   - Penalties

**Done!** All info displayed.

---

### Task 4: Delete an Extraction (5 seconds)

1. **Find** document with ✅ status
2. **Click** 🗑️ button in actions column
3. **Confirm** (extraction deleted immediately)
4. **See** status change to ⏳

**Done!** Can re-analyze if needed.

---

### Task 5: Hide a Document (3 seconds)

1. **Find** any document
2. **Click** 👁️‍🗨️ button
3. **See** document disappear

**To show again:**
1. **Check** "☑️ Afficher documents masqués"
2. **Find** document (now with 👁️‍🗨️ icon)
3. **Click** 👁️ button

**Done!** Document hidden/shown.

---

### Task 6: Filter Documents (2 seconds)

**By Status:**
1. **Click** "Filtrer par statut" dropdown
2. **Choose:**
   - "Tous" - Show all
   - "Analysés" - Only analyzed (✅)
   - "Non analysés" - Only pending (⏳)

**By Visibility:**
1. **Toggle** "☑️ Afficher documents masqués"
   - Checked: Show hidden documents
   - Unchecked: Hide them

**Done!** List filtered.

---

## 📊 Understanding the Interface

### Document List Columns:

```
┌─────────────────────────────────────────────────────────┐
│ [Name + Size]  [Upload Date]  [Status]  [Actions]      │
└─────────────────────────────────────────────────────────┘
```

1. **Name + Size**
   - 📄 = Visible document
   - 👁️‍🗨️ = Hidden document
   - Size in KB

2. **Upload Date**
   - 📅 YYYY-MM-DD HH:MM
   - When document was added/modified

3. **Status**
   - ✅ Analysé = Extraction complete
   - ⏳ Non analysé = Not yet analyzed

4. **Actions**
   - 🔍 = Analyze (only if not analyzed)
   - 🗑️ = Delete extraction (only if analyzed)
   - 👁️‍🗨️ = Hide document
   - 👁️ = Show document (if hidden)

### Status Indicators:

| Icon | Meaning | Action Available |
|------|---------|------------------|
| ✅ Analysé | Document analyzed | View, Delete, Hide |
| ⏳ Non analysé | Not yet analyzed | Analyze, Hide |
| 📄 | Visible document | All actions |
| 👁️‍🗨️ | Hidden document | Show, other actions |

---

## 💡 Pro Tips

### Tip 1: Use Filters Efficiently
- **Analyzing multiple docs?** Filter "Non analysés" to see what's left
- **Reviewing results?** Filter "Analysés" to see completed work
- **Cleaning up?** Show hidden docs to permanently delete them

### Tip 2: Auto-Rename is Smart
The system extracts:
- **Title** from document content
- **Country/Region** from metadata
- **Date** from effective date

Example transformations:
```
Before: "DIRECTIVE (UE) 20192161 DU PARLEMENT EUROPÉEN.html"
After:  "Consumer_Rights_European_Union_2019-11-27.html"

Before: "regulation-final-version-2024.pdf"
After:  "AI_Act_European_Union_2024-07-12.pdf"
```

### Tip 3: Cache Saves Money
- ✅ Keep "💾 Utiliser cache" checked
- First analysis: Uses Bedrock API (costs money, takes time)
- Subsequent: Uses cache (free, instant)
- Delete extraction to force re-analysis

### Tip 4: Hide vs Delete
- **Hide** = Document stays, just hidden from view
  - Use for: Test files, duplicates, irrelevant docs
  - Benefit: Can unhide later
  
- **Delete extraction** = Removes analysis results only
  - Use for: Outdated analysis, errors, re-analysis needed
  - Benefit: Source document stays

### Tip 5: Batch Operations
Want to analyze multiple documents?
1. Filter "Non analysés"
2. Click 🔍 on each one
3. Each analysis runs independently
4. Check back in 5-10 minutes

---

## 🔧 Troubleshooting

### Problem: "No documents showing"
**Solution:** Check if "Afficher documents masqués" is unchecked and all docs are hidden

### Problem: "Can't delete extraction"
**Solution:** Make sure document has ✅ status (analyzed)

### Problem: "Upload not working"
**Solution:** 
- Check file format (HTML, XML, PDF, TXT only)
- Ensure AWS credentials configured
- Try with "Utiliser cache" unchecked

### Problem: "Extraction taking too long"
**Solution:**
- Large documents (>5MB) take 3-5 minutes
- Check AWS Bedrock quota
- Try smaller document first

### Problem: "Suggested filename looks wrong"
**Solution:**
- Auto-rename is based on extracted content
- If extraction failed, name may be generic
- You can manually rename the file later

---

## 📚 File Locations

### Raw Documents:
```
data/raw/directives/
├── document1.html
├── document2.xml
└── document3.pdf
```

### Extraction Results:
```
data/generated/extracted_directives/
├── document1_extracted.json
├── document2_extracted.json
└── document3_extracted.json
```

### Hidden Documents List:
```
data/generated/.hidden_documents.json
```

---

## 🎓 Learning Path

### Beginner (5 minutes):
1. ✅ Upload one document
2. ✅ Analyze it
3. ✅ View results

### Intermediate (10 minutes):
1. ✅ Analyze existing documents
2. ✅ Use filters
3. ✅ Hide/show documents

### Advanced (15 minutes):
1. ✅ Delete old extractions
2. ✅ Re-analyze with different settings
3. ✅ Organize with hide/show
4. ✅ Use filters for workflow

---

## 🆘 Need Help?

### Documentation:
- `doc/REGULATORY_ANALYSIS_IMPROVEMENTS.md` - Detailed features
- `doc/UI_FLOW_DIAGRAM.md` - Visual workflows
- `doc/BEFORE_AFTER_COMPARISON.md` - What changed

### Key Files:
- `scripts/app.py` - Main application
- `scripts/document_analysis_helper.py` - Helper functions

### Common Questions:

**Q: Can I analyze multiple documents at once?**
A: Not in bulk, but you can start multiple analyses (they run independently)

**Q: What happens to hidden documents?**
A: They stay in `data/raw/directives/` but don't show in the list (unless you check "Afficher masqués")

**Q: Can I recover deleted extractions?**
A: No, but you can re-analyze the document (uses cache if available)

**Q: Does auto-rename change the actual file?**
A: No, it just suggests a name. The original file stays unchanged.

**Q: How do I permanently delete a document?**
A: Delete the file from `data/raw/directives/` manually (not through UI)

---

## 🎉 You're Ready!

You now know how to:
- ✅ Upload and analyze documents
- ✅ View extraction results
- ✅ Delete old extractions
- ✅ Hide/show documents
- ✅ Filter efficiently
- ✅ Use auto-rename

**Start analyzing regulatory documents now!**

---

**Last Updated:** November 2, 2025
**Version:** 2.0 (Complete Redesign)

