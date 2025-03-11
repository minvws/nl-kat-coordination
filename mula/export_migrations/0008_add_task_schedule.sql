CREATE TABLE schedules (
    id UUID NOT NULL, 
    scheduler_id VARCHAR NOT NULL, 
    hash VARCHAR(32), 
    data JSONB NOT NULL, 
    enabled BOOLEAN NOT NULL, 
    schedule VARCHAR, 
    deadline_at TIMESTAMP WITH TIME ZONE, 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    modified_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
    PRIMARY KEY (id), 
    UNIQUE (hash)
);
ALTER TABLE schedules OWNER TO mula_dba;
GRANT ALL ON schedules TO mula;


DROP INDEX ix_items_hash;
DROP TABLE items;

ALTER TABLE tasks ADD COLUMN schedule_id UUID;
ALTER TABLE tasks ADD COLUMN hash VARCHAR(32);
ALTER TABLE tasks ADD COLUMN priority INTEGER;
ALTER TABLE tasks ADD COLUMN data JSONB;

UPDATE tasks SET data = p_item -> 'data';
UPDATE tasks SET priority = (p_item ->> 'priority')::integer;
UPDATE tasks SET hash = p_item ->> 'hash';

ALTER TABLE tasks ALTER COLUMN data SET NOT NULL;
ALTER TABLE tasks ALTER COLUMN scheduler_id SET NOT NULL;
ALTER TABLE tasks ALTER COLUMN type SET NOT NULL;

DROP INDEX ix_tasks_p_item_hash;
CREATE INDEX ix_tasks_hash ON tasks (hash);

ALTER TABLE tasks ADD FOREIGN KEY(schedule_id) REFERENCES schedules (id) ON DELETE SET NULL;
ALTER TABLE tasks DROP COLUMN p_item;

INSERT INTO schedules (id, scheduler_id, hash, data, enabled, schedule, deadline_at, created_at, modified_at)
  SELECT DISTINCT ON (scheduler_id, hash)
    gen_random_uuid(),
    scheduler_id,
    hash,
    data,
    true,
    '0 0 * * *',
    now() + INTERVAL '1 day' * random(),
    now(),
    now()
FROM tasks ORDER BY scheduler_id, hash, created_at DESC;

UPDATE tasks SET schedule_id = schedules.id FROM schedules WHERE tasks.hash = schedules.hash;
