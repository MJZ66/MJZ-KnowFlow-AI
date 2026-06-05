-- Remove E2E/pytest users (keeps id=1 test, id=2 MJZ, id=60 seed admin)
BEGIN;

CREATE TEMP TABLE _test_user_ids AS
SELECT id FROM users
WHERE id NOT IN (1, 2, 60)
  AND (
    email ILIKE '%@example.com'
    OR email ILIKE 'e2e_%' OR username ILIKE 'e2e_%'
    OR email ILIKE 'rq_%' OR username ILIKE 'rq_%'
    OR email ILIKE 'pw_%' OR username ILIKE 'pw_%'
    OR email ILIKE 'pwd_%' OR username ILIKE 'pwd_%'
  );

UPDATE knowledge_bases SET publish_reviewed_by = NULL
WHERE publish_reviewed_by IN (SELECT id FROM _test_user_ids);

UPDATE operation_logs SET user_id = NULL
WHERE user_id IN (SELECT id FROM _test_user_ids);

DELETE FROM rag_references WHERE message_id IN (
  SELECT m.id FROM chat_messages m
  JOIN chat_sessions s ON s.id = m.session_id
  WHERE s.user_id IN (SELECT id FROM _test_user_ids)
     OR s.knowledge_base_id IN (
       SELECT id FROM knowledge_bases WHERE user_id IN (SELECT id FROM _test_user_ids)
     )
);

DELETE FROM chat_messages WHERE session_id IN (
  SELECT id FROM chat_sessions
  WHERE user_id IN (SELECT id FROM _test_user_ids)
     OR knowledge_base_id IN (
       SELECT id FROM knowledge_bases WHERE user_id IN (SELECT id FROM _test_user_ids)
     )
);

DELETE FROM chat_sessions
WHERE user_id IN (SELECT id FROM _test_user_ids)
   OR knowledge_base_id IN (
     SELECT id FROM knowledge_bases WHERE user_id IN (SELECT id FROM _test_user_ids)
   );

DELETE FROM document_chunks WHERE document_id IN (
  SELECT d.id FROM documents d
  JOIN knowledge_bases kb ON kb.id = d.knowledge_base_id
  WHERE kb.user_id IN (SELECT id FROM _test_user_ids)
);

DELETE FROM documents WHERE knowledge_base_id IN (
  SELECT id FROM knowledge_bases WHERE user_id IN (SELECT id FROM _test_user_ids)
);

DELETE FROM knowledge_base_members WHERE knowledge_base_id IN (
  SELECT id FROM knowledge_bases WHERE user_id IN (SELECT id FROM _test_user_ids)
);

DELETE FROM knowledge_bases WHERE user_id IN (SELECT id FROM _test_user_ids);

DELETE FROM users WHERE id IN (SELECT id FROM _test_user_ids);

UPDATE users SET role = 'SUPER_ADMIN' WHERE email = '2429448372@qq.com';

COMMIT;
