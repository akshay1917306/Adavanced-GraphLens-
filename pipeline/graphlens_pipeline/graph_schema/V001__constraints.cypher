// Every entity has one stable id. Entities of all types share the label Entity.
CREATE CONSTRAINT entity_id IF NOT EXISTS FOR (e:Entity) REQUIRE e.id IS UNIQUE;
