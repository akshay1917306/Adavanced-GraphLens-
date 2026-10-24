// Community report embeddings: BAAI/bge-base-en-v1.5, 768 numbers per report, compared by cosine.
CREATE VECTOR INDEX community_report_embedding IF NOT EXISTS FOR (c:Community) ON (c.embedding)
OPTIONS {indexConfig: {`vector.dimensions`: 768, `vector.similarity_function`: 'cosine'}};
