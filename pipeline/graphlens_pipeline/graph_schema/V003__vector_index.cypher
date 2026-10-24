// Entity embeddings: BAAI/bge-base-en-v1.5 gives 768 numbers per text, compared by cosine.
CREATE VECTOR INDEX entity_embedding IF NOT EXISTS FOR (e:Entity) ON (e.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};
