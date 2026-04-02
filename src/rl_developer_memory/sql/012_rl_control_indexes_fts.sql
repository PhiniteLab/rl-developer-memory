CREATE INDEX IF NOT EXISTS idx_issue_patterns_rl_lookup
    ON issue_patterns(memory_kind, problem_family, theorem_claim_type, validation_tier, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_issue_variants_rl_lookup
    ON issue_variants(pattern_id, algorithm_family, runtime_stage, updated_at DESC);
CREATE INDEX IF NOT EXISTS idx_issue_episodes_rl_lookup
    ON issue_episodes(pattern_id, variant_id, created_at DESC);

UPDATE issue_variants
SET search_text = trim(
    COALESCE(search_text, '') || ' ' ||
    COALESCE(algorithm_family, '') || ' ' ||
    COALESCE(runtime_stage, '') || ' ' ||
    COALESCE(variant_profile_json, '') || ' ' ||
    COALESCE(sim2real_profile_json, '')
);

UPDATE issue_episodes
SET search_text = trim(
    COALESCE(search_text, '') || ' ' ||
    COALESCE(run_manifest_json, '') || ' ' ||
    COALESCE(metrics_json, '') || ' ' ||
    COALESCE(artifact_refs_json, '') || ' ' ||
    COALESCE(evidence_json, '')
);

DROP TABLE IF EXISTS issue_patterns_fts;
CREATE VIRTUAL TABLE issue_patterns_fts USING fts5(
    title,
    canonical_symptom,
    canonical_fix,
    prevention_rule,
    verification_steps,
    tags,
    root_cause_class,
    error_family,
    domain,
    memory_kind,
    problem_family,
    theorem_claim_type,
    validation_tier,
    problem_profile
);

INSERT INTO issue_patterns_fts(
    rowid, title, canonical_symptom, canonical_fix, prevention_rule, verification_steps,
    tags, root_cause_class, error_family, domain, memory_kind, problem_family,
    theorem_claim_type, validation_tier, problem_profile
)
SELECT
    id, title, canonical_symptom, canonical_fix, prevention_rule, verification_steps,
    tags, root_cause_class, error_family, domain, memory_kind, problem_family,
    theorem_claim_type, validation_tier, problem_profile_json
FROM issue_patterns;

INSERT INTO issue_variants_fts(issue_variants_fts) VALUES('rebuild');
INSERT INTO issue_episodes_fts(issue_episodes_fts) VALUES('rebuild');

INSERT OR REPLACE INTO app_metadata(key, value, updated_at)
VALUES ('rl_control_indexes_fts', 'enabled', strftime('%Y-%m-%dT%H:%M:%SZ', 'now'));
