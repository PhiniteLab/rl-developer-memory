ALTER TABLE issue_patterns ADD COLUMN memory_kind TEXT NOT NULL DEFAULT 'failure_pattern';
ALTER TABLE issue_patterns ADD COLUMN problem_family TEXT NOT NULL DEFAULT 'generic';
ALTER TABLE issue_patterns ADD COLUMN theorem_claim_type TEXT NOT NULL DEFAULT 'none';
ALTER TABLE issue_patterns ADD COLUMN validation_tier TEXT NOT NULL DEFAULT 'observed';
ALTER TABLE issue_patterns ADD COLUMN problem_profile_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE issue_patterns ADD COLUMN validation_json TEXT NOT NULL DEFAULT '{}';

ALTER TABLE issue_variants ADD COLUMN algorithm_family TEXT NOT NULL DEFAULT '';
ALTER TABLE issue_variants ADD COLUMN runtime_stage TEXT NOT NULL DEFAULT '';
ALTER TABLE issue_variants ADD COLUMN variant_profile_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE issue_variants ADD COLUMN sim2real_profile_json TEXT NOT NULL DEFAULT '{}';

ALTER TABLE issue_episodes ADD COLUMN run_manifest_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE issue_episodes ADD COLUMN metrics_json TEXT NOT NULL DEFAULT '{}';
ALTER TABLE issue_episodes ADD COLUMN artifact_refs_json TEXT NOT NULL DEFAULT '[]';
ALTER TABLE issue_episodes ADD COLUMN evidence_json TEXT NOT NULL DEFAULT '{}';

INSERT OR REPLACE INTO app_metadata(key, value, updated_at)
VALUES ('rl_control_extension', 'enabled', strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));
