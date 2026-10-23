-- Run with psql against a representative active dataset before a Phase 2 release.
-- Replace the literal filter values with common and worst-case production-like inputs.
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT r.id, r.name, r.rating, r.average_cost_minor
FROM restaurants AS r
JOIN dataset_versions AS dv ON dv.id = r.dataset_version_id
WHERE dv.status = 'active'
  AND r.city_normalized = 'bangalore'
  AND r.locality_normalized = 'indiranagar'
  AND r.currency_code = 'INR'
  AND r.average_cost_minor BETWEEN 60001 AND 150000
  AND r.rating >= 4.0
  AND EXISTS (
    SELECT 1
    FROM restaurant_cuisines AS rc
    WHERE rc.restaurant_id = r.id
      AND rc.cuisine_normalized IN ('italian', 'chinese')
  )
ORDER BY r.rating DESC NULLS LAST, r.votes DESC NULLS LAST, r.name_normalized, r.source_key
LIMIT 500;
