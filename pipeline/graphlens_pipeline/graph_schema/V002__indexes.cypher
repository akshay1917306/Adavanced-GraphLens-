// Look-ups by type, by name and by index version (to find what one load wrote).
CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type);
CREATE INDEX entity_name IF NOT EXISTS FOR (e:Entity) ON (e.name);
CREATE INDEX entity_index_version IF NOT EXISTS FOR (e:Entity) ON (e.index_version);
CREATE FULLTEXT INDEX entity_text IF NOT EXISTS FOR (e:Entity) ON EACH [e.name, e.aliases_text];
