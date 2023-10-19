WITH filtered AS (
    SELECT m.id, array_agg(m.mime_type) AS mime_types FROM (
        SELECT raw.id, boefje_id, unnest(mime_types) AS mime_type
        FROM raw_file raw JOIN boefje_meta b ON boefje_meta_id = b.id
    ) m

    WHERE m.mime_type NOT LIKE concat('boefje/', m.boefje_id, '-%')
    GROUP BY m.id
)
UPDATE raw_file r SET mime_types = filtered.mime_types FROM filtered WHERE r.id = filtered.id;
