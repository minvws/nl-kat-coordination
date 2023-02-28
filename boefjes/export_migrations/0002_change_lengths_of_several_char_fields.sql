-- These were not added yet but should have been
ALTER TABLE organisation ADD CONSTRAINT organisation_id UNIQUE (id);
ALTER TABLE repository ADD CONSTRAINT repository_id UNIQUE (id);

-- Update setting table
ALTER TABLE setting ADD COLUMN plugin_id VARCHAR(32) NOT NULL;
ALTER TABLE setting ALTER COLUMN key TYPE VARCHAR(128);
ALTER TABLE setting ALTER COLUMN value TYPE VARCHAR(128);

ALTER TABLE plugin_state ADD CONSTRAINT unique_plugin_per_repo_per_org UNIQUE (plugin_id, organisation_pk, repository_pk);
ALTER TABLE setting ADD CONSTRAINT unique_keys_per_organisation_per_plugin UNIQUE (key, organisation_pk, plugin_id);


ALTER TABLE plugin_state DROP CONSTRAINT plugin_state_plugin_id_key;
