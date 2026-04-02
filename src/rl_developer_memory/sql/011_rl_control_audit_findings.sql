CREATE TABLE IF NOT EXISTS audit_findings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER,
    variant_id INTEGER,
    episode_id INTEGER,
    audit_type TEXT NOT NULL DEFAULT 'runtime',
    severity TEXT NOT NULL DEFAULT 'warning',
    status TEXT NOT NULL DEFAULT 'open',
    summary TEXT NOT NULL DEFAULT '',
    payload_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    FOREIGN KEY(pattern_id) REFERENCES issue_patterns(id) ON DELETE SET NULL,
    FOREIGN KEY(variant_id) REFERENCES issue_variants(id) ON DELETE SET NULL,
    FOREIGN KEY(episode_id) REFERENCES issue_episodes(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_findings_pattern
    ON audit_findings(pattern_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_findings_variant
    ON audit_findings(variant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_findings_episode
    ON audit_findings(episode_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_findings_status
    ON audit_findings(status, severity, created_at DESC);

CREATE TABLE IF NOT EXISTS artifact_references (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pattern_id INTEGER,
    variant_id INTEGER,
    episode_id INTEGER NOT NULL,
    kind TEXT NOT NULL DEFAULT '',
    uri TEXT NOT NULL DEFAULT '',
    description TEXT NOT NULL DEFAULT '',
    checksum TEXT NOT NULL DEFAULT '',
    bytes INTEGER NOT NULL DEFAULT 0,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    FOREIGN KEY(pattern_id) REFERENCES issue_patterns(id) ON DELETE SET NULL,
    FOREIGN KEY(variant_id) REFERENCES issue_variants(id) ON DELETE SET NULL,
    FOREIGN KEY(episode_id) REFERENCES issue_episodes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_artifact_references_episode
    ON artifact_references(episode_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_artifact_references_pattern
    ON artifact_references(pattern_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_artifact_references_variant
    ON artifact_references(variant_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_artifact_references_kind
    ON artifact_references(kind, created_at DESC);

INSERT OR REPLACE INTO app_metadata(key, value, updated_at)
VALUES ('rl_control_audit_findings', 'enabled', strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));
