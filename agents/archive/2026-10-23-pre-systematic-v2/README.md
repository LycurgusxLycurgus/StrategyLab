# Pre-systematic-v2 document archive

This directory preserves the 24 listed documents as exact-byte snapshots from before the systematic phase and operator replacement dated 2026-10-23. `manifest.json` is the inventory: `source_path` is relative to the repository root; `archive_path` is the archived file's full repository-relative path; `sha256` and `bytes` describe the archived bytes. The source-to-archive hash and size comparison was verified before the active documents were edited.

The archived operator and ten former phase prompts retain their original repository-relative directory structure beneath this archive. This is a historical recovery copy, not an active prompt set. The application discovers prompts only from direct `*.md` files in the configured prompt directory; nested archive documents are not auto-discovered. Existing runtime paths, APIs, and workflow identifiers are not renamed by this documentation archive.

Restore only after explicit user authorization. Restoring a snapshot over an active path would replace the current document and must not happen automatically. Use the manifest to select the intended file, verify its SHA-256, and copy it deliberately to the matching `source_path`; never bulk-restore the archive as part of normal startup or prompt discovery.
