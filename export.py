#!/usr/bin/env python3
"""Export MacWhisper transcription sessions to Obsidian markdown notes."""

import json
import os
import re
import sqlite3
import sys
from pathlib import Path

DB_PATH = Path.home() / "Library/Application Support/MacWhisper/Database/main.sqlite"
OUTPUT_DIR = Path("./output")
STATE_FILE = Path(".export_state.json")


def format_duration(seconds):
    """Convert float seconds to HH:MM:SS string."""
    if seconds is None or seconds <= 0:
        return "00:00:00"
    total = int(seconds)
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    return f"{h:02d}:{m:02d}:{s:02d}"


def sanitize_filename(title):
    """Replace unsafe characters and trim to 200 chars."""
    name = re.sub(r'[/\\:*?"<>|]', "-", title)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:200]


def get_title(session):
    """Pick the best available title by priority."""
    for field in ("userChosenTitle", "aiTitle", "aiSummaryShort", "originalFilename"):
        value = session.get(field)
        if value and value.strip():
            return value.strip()
    return "Untitled"


def render_note(session):
    """Build the full markdown string for an Obsidian note."""
    title = get_title(session)
    date = (session["dateCreated"] or "")[:10]
    duration = format_duration(session["playbackDuration"])
    language = session.get("detectedLanguage") or ""
    source = session.get("originalFilename") or ""
    uuid_hex = session["id"]

    lines = [
        "---",
        f"date: {date}",
        f'duration: "{duration}"',
        f"language: {language}",
        f"source: {source}",
        f"macwhisper_id: {uuid_hex}",
        "---",
        "",
        f"# {title}",
    ]

    ai_summary = session.get("aiSummary")
    if ai_summary and ai_summary.strip():
        lines += ["", "## Summary", "", ai_summary.strip()]

    full_text = session.get("fullText")
    if full_text and full_text.strip():
        lines += ["", "## Transcript", "", full_text.strip()]

    lines.append("")  # trailing newline
    return "\n".join(lines)


def load_state():
    """Load the incremental export state from disk."""
    if STATE_FILE.exists():
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("exported", {})
    return {}


def save_state(state):
    """Persist the export state to disk."""
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump({"exported": state}, f, ensure_ascii=False, indent=2)
        f.write("\n")


def get_sessions(conn):
    """Fetch all sessions from the MacWhisper database."""
    cursor = conn.execute(
        """
        SELECT
            hex(id) AS id,
            dateCreated,
            dateUpdated,
            userChosenTitle,
            aiTitle,
            aiSummaryShort,
            aiSummary,
            fullText,
            playbackDuration,
            detectedLanguage,
            originalFilename
        FROM session
        """
    )
    columns = [desc[0] for desc in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]


def export_session(session, output_dir, used_filenames):
    """Write a single session to a markdown file. Returns the filename."""
    title = get_title(session)
    date = (session["dateCreated"] or "")[:10]
    base = sanitize_filename(f"{date} {title}")

    # Deduplicate filenames within a single export run
    filename = base + ".md"
    counter = 2
    while filename in used_filenames:
        filename = f"{base} ({counter}).md"
        counter += 1
    used_filenames.add(filename)

    content = render_note(session)
    filepath = output_dir / filename
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)

    return filename


def main():
    if not DB_PATH.exists():
        print(f"Error: database not found at {DB_PATH}", file=sys.stderr)
        sys.exit(1)

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        state = load_state()
        sessions = get_sessions(conn)

        new_count = 0
        updated_count = 0
        skipped_count = 0

        new_state = dict(state)
        used_filenames = set()

        for session in sessions:
            uuid_hex = session["id"]
            date_updated = session["dateUpdated"] or ""

            prev = state.get(uuid_hex)
            if isinstance(prev, dict):
                prev_date = prev.get("dateUpdated", "")
                prev_filename = prev.get("filename")
            elif isinstance(prev, str):
                # Migrate from old format (just dateUpdated string)
                prev_date = prev
                prev_filename = None
            else:
                prev_date = None
                prev_filename = None

            if prev_date is None:
                # New session
                fname = export_session(session, OUTPUT_DIR, used_filenames)
                new_state[uuid_hex] = {"dateUpdated": date_updated, "filename": fname}
                new_count += 1
            elif prev_date != date_updated:
                # Updated session — remove old file if title changed
                if prev_filename:
                    old_path = OUTPUT_DIR / prev_filename
                    if old_path.exists():
                        old_path.unlink()

                fname = export_session(session, OUTPUT_DIR, used_filenames)
                new_state[uuid_hex] = {"dateUpdated": date_updated, "filename": fname}
                updated_count += 1
            else:
                # Keep existing filename in used set to avoid collisions
                if prev_filename:
                    used_filenames.add(prev_filename)
                skipped_count += 1

        save_state(new_state)

        print(
            f"Done: {new_count} new, {updated_count} updated, "
            f"{skipped_count} skipped (total {len(sessions)} sessions)"
        )
    finally:
        conn.close()


if __name__ == "__main__":
    main()
