use anyhow::{Context, Result};
use chrono::Utc;
use rayon::prelude::*;
use rusqlite::{params, Connection};
use std::collections::HashSet;
use std::fs;
use std::path::{Path, PathBuf};
use walkdir::WalkDir;

const DB_NAME: &str = ".backend/backend.db";

fn main() -> Result<()> {
    let root = std::env::current_dir()?;
    let db_path = root.join(DB_NAME);

    initialize_backend(&root)?;

    let mut conn = Connection::open(&db_path)?;
    conn.execute("PRAGMA journal_mode = WAL;", [])?;
    conn.execute("PRAGMA synchronous = NORMAL;", [])?;

    let changed_folders = scan_and_index(&mut conn, &root)?;
    regenerate_agents(&root, &changed_folders)?;

    println!(
        "Scan complete: {} folders updated",
        changed_folders.len()
    );
    Ok(())
}

fn initialize_backend(root: &Path) -> Result<()> {
    let backend = root.join(".backend");
    fs::create_dir_all(&backend)?;

    let db_path = root.join(DB_NAME);
    let conn = Connection::open(&db_path)?;
    conn.execute_batch(
        "
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            size INTEGER NOT NULL,
            modified INTEGER NOT NULL,
            extension TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_path ON files(path);
        ",
    )?;
    Ok(())
}

fn scan_and_index(conn: &mut Connection, root: &Path) -> Result<HashSet<PathBuf>> {
    let mut changed_folders = HashSet::new();

    let entries: Vec<_> = WalkDir::new(root)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .filter(|e| {
            let p = e.path();
            !p.ends_with("AGENT.md")
                && !p.components().any(|c| {
                    let s = c.as_os_str().to_string_lossy();
                    s == ".git" || s == ".backend" || s == "target" || s == "node_modules"
                })
        })
        .collect();

    let file_data: Vec<_> = entries
        .par_iter()
        .filter_map(|entry| {
            let path = entry.path();
            let metadata = fs::metadata(path).ok()?;
            let modified = metadata
                .modified()
                .ok()?
                .duration_since(std::time::UNIX_EPOCH)
                .ok()?
                .as_secs() as i64;
            Some((
                path.to_path_buf(),
                metadata.len() as i64,
                modified,
                path.extension()
                    .and_then(|e| e.to_str())
                    .unwrap_or("")
                    .to_string(),
            ))
        })
        .collect();

    let tx = conn.transaction()?;
    {
        let mut select_stmt =
            tx.prepare("SELECT size, modified FROM files WHERE path = ?1")?;
        let mut insert_stmt = tx.prepare(
            "INSERT OR REPLACE INTO files (path, size, modified, extension)
             VALUES (?1, ?2, ?3, ?4)",
        )?;

        for (path, size, modified, ext) in &file_data {
            let path_str = path.to_string_lossy();

            let changed = {
                let mut rows = select_stmt
                    .query(params![path_str.as_ref()])
                    .context("querying file index")?;
                if let Some(row) = rows.next()? {
                    let old_size: i64 = row.get(0)?;
                    let old_modified: i64 = row.get(1)?;
                    old_size != *size || old_modified != *modified
                } else {
                    true
                }
            };

            if changed {
                insert_stmt
                    .execute(params![path_str.as_ref(), size, modified, ext])
                    .context("inserting file record")?;
                if let Some(parent) = path.parent() {
                    changed_folders.insert(parent.to_path_buf());
                }
            }
        }
    }
    tx.commit()?;
    Ok(changed_folders)
}

fn regenerate_agents(root: &Path, changed_folders: &HashSet<PathBuf>) -> Result<()> {
    for folder in changed_folders {
        // Read directory entries directly instead of querying with LIKE
        // (avoids prefix-matching bugs across sibling directories)
        let entries: Vec<_> = fs::read_dir(folder)?
            .filter_map(|e| e.ok())
            .filter(|e| e.file_type().map(|ft| ft.is_file()).unwrap_or(false))
            .filter(|e| e.file_name() != "AGENT.md")
            .collect();

        if entries.is_empty() {
            continue;
        }

        let folder_name = folder
            .strip_prefix(root)
            .unwrap_or(folder)
            .to_string_lossy();
        let display_name = if folder_name.is_empty() {
            ".".to_string()
        } else {
            folder_name.to_string()
        };

        let mut content = format!(
            "# AGENT - {}\n\nLast Updated: {}\n\n## Files\n\n",
            display_name,
            Utc::now().format("%Y-%m-%d %H:%M:%S UTC")
        );

        let mut sorted_entries: Vec<_> = entries
            .iter()
            .filter_map(|e| {
                let meta = e.metadata().ok()?;
                Some((e.file_name().to_string_lossy().to_string(), meta.len()))
            })
            .collect();
        sorted_entries.sort_by(|a, b| a.0.cmp(&b.0));

        for (name, size) in &sorted_entries {
            content.push_str(&format!("- `{}` ({} bytes)\n", name, size));
        }

        let agent_path = folder.join("AGENT.md");
        if let Ok(existing) = fs::read_to_string(&agent_path) {
            // Compare ignoring the timestamp line to avoid unnecessary rewrites
            let strip_ts = |s: &str| -> String {
                s.lines()
                    .filter(|l| !l.starts_with("Last Updated:"))
                    .collect::<Vec<_>>()
                    .join("\n")
            };
            if strip_ts(&existing) == strip_ts(&content) {
                continue;
            }
        }

        fs::write(&agent_path, &content)
            .with_context(|| format!("writing {}", agent_path.display()))?;
    }
    Ok(())
}
