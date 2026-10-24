// Communities found by hierarchical Leiden. Entities point at them with IN_COMMUNITY (one per
// level) and a community points at its parent with CHILD_OF.
CREATE CONSTRAINT community_id IF NOT EXISTS FOR (c:Community) REQUIRE c.id IS UNIQUE;
CREATE INDEX community_level IF NOT EXISTS FOR (c:Community) ON (c.level);
CREATE INDEX community_index_version IF NOT EXISTS FOR (c:Community) ON (c.index_version);
