# macwhisper2obsidian

Export transcription sessions from [MacWhisper](https://goodsnooze.gumroad.com/l/macwhisper) into markdown notes for [Obsidian](https://obsidian.md).

The script reads MacWhisper's SQLite database, converts each transcription session into a `.md` file with YAML frontmatter, and supports incremental export — only new or updated sessions are written on subsequent runs.

## Requirements

- Python 3.6+
- macOS with MacWhisper installed

No external dependencies are needed — only the Python standard library.

## Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/your-user/macwhisper2obsidian.git
   cd macwhisper2obsidian
   ```

2. Copy the example config and edit paths if needed:
   ```bash
   cp config.example.json config.json
   ```

3. Edit `config.json`:
   ```json
   {
     "db_path": "~/Library/Application Support/MacWhisper/Database/main.sqlite",
     "output_dir": "./output",
     "state_file": ".export_state.json"
   }
   ```
   - `db_path` — path to the MacWhisper SQLite database (`~` is expanded automatically)
   - `output_dir` — directory where markdown files will be written
   - `state_file` — file that tracks which sessions have already been exported

## Usage

```bash
python3 export.py
```

Output example:
```
Done: 12 new, 0 updated, 0 skipped (total 12 sessions)
```

Run the script again to pick up only new or changed sessions.

## Output format

Each exported file looks like this:

```markdown
---
date: 2025-06-15
duration: "00:12:34"
language: en
source: recording.m4a
macwhisper_id: AABBCCDD...
---

# Meeting notes

## Summary

AI-generated summary (if available).

## Transcript

Full transcription text.
```

Fields `Summary` and `Transcript` are included only when present in the database.
