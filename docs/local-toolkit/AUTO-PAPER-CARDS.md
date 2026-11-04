# Source-linked paper Flash Cards

Reading-task saves generate cards locally from the user's notes. Existing saved notes are converted when that paper's reading checklist is opened. Standard reading tasks use short question templates. Answers split on nonempty lines and sentence boundaries, preserving the original wording. Reading Q/A items, extension problems, search keywords, selected classifications, relationships and dataset names/source papers also produce cards where source content exists. Missing answers are not inferred; uploaded diagrams need a written explanation before a Q/A card can be made.

This is deterministic splitting, not model-based semantic summarization. Cards show their source task with a navigation button, so conditions and surrounding context can be checked. Relationship evidence status is preserved. Manual cards remain editable. The daily Quiz enrollment checkbox and existing content-aware review schedule remain in use; card creation alone does not mark the paper or its last reading task complete.

Generated IDs are stable by source. Server-only provenance stores the last generated text. If the user edits either side, that card becomes manual and stops auto-updating. Removing an automatic card suppresses re-creation; undoing removal restores it. Source updates affect unedited generated cards. The 100-card limit is explicit and reports remaining omitted points. A client merge preserves edits and removals made while autosave is in flight. Existing daily Quiz snapshots remain frozen.

Validation includes note splitting, incomplete Q/A, duplicate prevention, stable updates, manual overrides, removal suppression, capacity reporting and in-flight client edits. Browser QA uses only the isolated localhost 8772 database.
