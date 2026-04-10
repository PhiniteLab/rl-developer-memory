-- 013: Performance indexes for metrics & health queries
--
-- retrieval_candidates.created_at is used by metrics_summary for
-- safe-override / shadow-promote / preference-rule counting.
CREATE INDEX IF NOT EXISTS idx_retrieval_candidates_created
    ON retrieval_candidates(created_at);

-- issue_variants.status is used by metrics_summary for provisional/archived counts.
CREATE INDEX IF NOT EXISTS idx_issue_variants_status
    ON issue_variants(status);

-- feedback_events.created_at + feedback_type covers the GROUP BY query.
CREATE INDEX IF NOT EXISTS idx_feedback_events_created_type
    ON feedback_events(created_at, feedback_type);
