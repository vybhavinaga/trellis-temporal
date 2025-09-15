-- Orders table (minimal)
CREATE TABLE IF NOT EXISTS orders (
  order_id   TEXT PRIMARY KEY,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Idempotent payments (payment_id is the idempotency key)
CREATE TABLE IF NOT EXISTS payments (
  payment_id  TEXT PRIMARY KEY,
  order_id    TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'created',
  amount      INTEGER,
  created_at  TIMESTAMP DEFAULT NOW()
);

-- Optional event log for observability
CREATE TABLE IF NOT EXISTS events (
  id         BIGSERIAL PRIMARY KEY,
  order_id   TEXT NOT NULL,
  event_type TEXT NOT NULL,
  payload    JSONB,
  created_at TIMESTAMP DEFAULT NOW()
);

