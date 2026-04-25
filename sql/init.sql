CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS baseline_story_events (
    seq_id serial PRIMARY KEY,
    event_id text UNIQUE NOT NULL,
    source text NOT NULL,
    occurred_at timestamptz NOT NULL,
    text text NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS events (
    event_id text PRIMARY KEY,
    source text NOT NULL,
    occurred_at timestamptz NOT NULL,
    ingested_at timestamptz NOT NULL DEFAULT now(),
    text text NOT NULL,
    normalized_text text NOT NULL,
    fingerprint text NOT NULL,
    cluster_id uuid,
    decision text,
    confidence double precision,
    gate1_score double precision,
    gate2_score double precision,
    judge_confidence double precision,
    judge_decision text,
    semantic_score double precision,
    time_weight double precision,
    final_score double precision,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_events_fingerprint_occurred_at
    ON events (fingerprint, occurred_at DESC);

CREATE TABLE IF NOT EXISTS clusters (
    cluster_id uuid PRIMARY KEY,
    status text NOT NULL,
    first_seen_at timestamptz NOT NULL,
    last_seen_at timestamptz NOT NULL,
    member_count integer NOT NULL,
    exemplar_event_ids jsonb NOT NULL DEFAULT '[]'::jsonb,
    keywords jsonb NOT NULL DEFAULT '[]'::jsonb,
    summary_text text NOT NULL DEFAULT '',
    candidate_parent_cluster_id uuid,
    candidate_parent_score double precision
);

CREATE INDEX IF NOT EXISTS idx_clusters_last_seen_at
    ON clusters (last_seen_at DESC);

CREATE TABLE IF NOT EXISTS semantic_embeddings (
    entity_type text NOT NULL CHECK (entity_type IN ('event', 'cluster')),
    entity_id text NOT NULL,
    embedding vector(1024) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (entity_type, entity_id)
);

CREATE TABLE IF NOT EXISTS projection_embeddings (
    entity_type text NOT NULL CHECK (entity_type IN ('event', 'cluster')),
    entity_id text NOT NULL,
    embedding vector(1024) NOT NULL,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (entity_type, entity_id)
);

CREATE INDEX IF NOT EXISTS idx_semantic_embeddings_cluster_hnsw
    ON semantic_embeddings USING hnsw (embedding vector_cosine_ops)
    WHERE entity_type = 'cluster';

CREATE INDEX IF NOT EXISTS idx_projection_embeddings_cluster_hnsw
    ON projection_embeddings USING hnsw (embedding vector_cosine_ops)
    WHERE entity_type = 'cluster';

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'events' AND column_name = 'embedding'
    ) AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'events' AND column_name = 'projection_embedding'
    ) THEN
        EXECUTE $sql$
            INSERT INTO projection_embeddings (entity_type, entity_id, embedding)
            SELECT 'event', event_id, COALESCE(projection_embedding, embedding)
            FROM events
            WHERE COALESCE(projection_embedding, embedding) IS NOT NULL
            ON CONFLICT (entity_type, entity_id) DO NOTHING
        $sql$;
    ELSIF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'events' AND column_name = 'embedding'
    ) THEN
        EXECUTE $sql$
            INSERT INTO projection_embeddings (entity_type, entity_id, embedding)
            SELECT 'event', event_id, embedding
            FROM events
            WHERE embedding IS NOT NULL
            ON CONFLICT (entity_type, entity_id) DO NOTHING
        $sql$;
    ELSIF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'events' AND column_name = 'projection_embedding'
    ) THEN
        EXECUTE $sql$
            INSERT INTO projection_embeddings (entity_type, entity_id, embedding)
            SELECT 'event', event_id, projection_embedding
            FROM events
            WHERE projection_embedding IS NOT NULL
            ON CONFLICT (entity_type, entity_id) DO NOTHING
        $sql$;
    END IF;

    IF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'clusters' AND column_name = 'centroid_embedding'
    ) AND EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'clusters' AND column_name = 'projection_centroid_embedding'
    ) THEN
        EXECUTE $sql$
            INSERT INTO projection_embeddings (entity_type, entity_id, embedding)
            SELECT 'cluster', cluster_id::text, COALESCE(projection_centroid_embedding, centroid_embedding)
            FROM clusters
            WHERE COALESCE(projection_centroid_embedding, centroid_embedding) IS NOT NULL
            ON CONFLICT (entity_type, entity_id) DO NOTHING
        $sql$;
    ELSIF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'clusters' AND column_name = 'centroid_embedding'
    ) THEN
        EXECUTE $sql$
            INSERT INTO projection_embeddings (entity_type, entity_id, embedding)
            SELECT 'cluster', cluster_id::text, centroid_embedding
            FROM clusters
            WHERE centroid_embedding IS NOT NULL
            ON CONFLICT (entity_type, entity_id) DO NOTHING
        $sql$;
    ELSIF EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'clusters' AND column_name = 'projection_centroid_embedding'
    ) THEN
        EXECUTE $sql$
            INSERT INTO projection_embeddings (entity_type, entity_id, embedding)
            SELECT 'cluster', cluster_id::text, projection_centroid_embedding
            FROM clusters
            WHERE projection_centroid_embedding IS NOT NULL
            ON CONFLICT (entity_type, entity_id) DO NOTHING
        $sql$;
    END IF;
END $$;

DROP INDEX IF EXISTS idx_clusters_centroid_hnsw;
DROP INDEX IF EXISTS idx_clusters_projection_centroid_hnsw;

ALTER TABLE events
    ADD COLUMN IF NOT EXISTS gate1_score double precision,
    ADD COLUMN IF NOT EXISTS gate2_score double precision,
    ADD COLUMN IF NOT EXISTS judge_confidence double precision,
    ADD COLUMN IF NOT EXISTS judge_decision text;

ALTER TABLE clusters
    ADD COLUMN IF NOT EXISTS summary_text text NOT NULL DEFAULT '';

ALTER TABLE events
    DROP COLUMN IF EXISTS embedding,
    DROP COLUMN IF EXISTS projection_embedding;

ALTER TABLE clusters
    DROP COLUMN IF EXISTS centroid_embedding,
    DROP COLUMN IF EXISTS projection_centroid_embedding;

CREATE TABLE IF NOT EXISTS merge_audit (
    merge_id uuid PRIMARY KEY,
    winner_cluster_id uuid NOT NULL,
    loser_cluster_id uuid NOT NULL,
    evidence_score double precision NOT NULL,
    evidence_summary jsonb NOT NULL DEFAULT '{}'::jsonb,
    merged_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS stream_events (
    stream_id bigserial PRIMARY KEY,
    event_type text NOT NULL,
    payload jsonb NOT NULL,
    emitted_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS runtime_state (
    key text PRIMARY KEY,
    bool_value boolean,
    updated_at timestamptz NOT NULL DEFAULT now()
);

DO $$
BEGIN
    IF EXISTS (
        SELECT 1
        FROM pg_attribute
        WHERE attrelid = 'semantic_embeddings'::regclass
          AND attname = 'embedding'
          AND atttypmod <> 1024
    ) OR EXISTS (
        SELECT 1
        FROM pg_attribute
        WHERE attrelid = 'projection_embeddings'::regclass
          AND attname = 'embedding'
          AND atttypmod <> 1024
    ) THEN
        DROP INDEX IF EXISTS idx_semantic_embeddings_cluster_hnsw;
        DROP INDEX IF EXISTS idx_projection_embeddings_cluster_hnsw;
        TRUNCATE TABLE merge_audit, semantic_embeddings, projection_embeddings, events, clusters RESTART IDENTITY;
        DELETE FROM stream_events;
        DELETE FROM runtime_state;
        ALTER TABLE semantic_embeddings
            ALTER COLUMN embedding TYPE vector(1024);
        ALTER TABLE projection_embeddings
            ALTER COLUMN embedding TYPE vector(1024);
    END IF;
END $$;
