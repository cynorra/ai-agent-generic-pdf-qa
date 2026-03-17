-- ============================================================
--  Supabase Schema — Run this in Supabase SQL Editor
--  Project: Generic AI Agent (Orders + Scheduling)
-- ============================================================

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================
-- BUSINESSES
-- ============================================================
CREATE TABLE IF NOT EXISTS businesses (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        TEXT NOT NULL,
    type        TEXT,                          -- e.g. 'restaurant', 'clinic', 'dryclean'
    pdf_path    TEXT,
    description TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CUSTOMERS
-- ============================================================
CREATE TABLE IF NOT EXISTS customers (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name         TEXT,
    phone        TEXT,
    email        TEXT,
    address      TEXT,
    business_id  UUID REFERENCES businesses(id),
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- SESSIONS (conversation sessions)
-- ============================================================
CREATE TABLE IF NOT EXISTS sessions (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id  UUID REFERENCES businesses(id),
    customer_id  UUID REFERENCES customers(id),
    status       TEXT DEFAULT 'active',        -- active | closed
    intent       TEXT,                         -- order | appointment | info | mixed
    context      JSONB DEFAULT '{}',
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- ORDERS
-- ============================================================
CREATE TABLE IF NOT EXISTS orders (
    id            UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id    UUID REFERENCES sessions(id),
    business_id   UUID REFERENCES businesses(id),
    customer_id   UUID REFERENCES customers(id),
    status        TEXT DEFAULT 'draft',        -- draft | confirmed | cancelled | completed
    items         JSONB DEFAULT '[]',          -- [{name, qty, price, modifiers, notes}]
    subtotal      NUMERIC(10,2) DEFAULT 0,
    tax           NUMERIC(10,2) DEFAULT 0,
    total         NUMERIC(10,2) DEFAULT 0,
    delivery_type TEXT,                        -- pickup | delivery
    address       TEXT,
    notes         TEXT,
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- APPOINTMENTS
-- ============================================================
CREATE TABLE IF NOT EXISTS appointments (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id      UUID REFERENCES sessions(id),
    business_id     UUID REFERENCES businesses(id),
    customer_id     UUID REFERENCES customers(id),
    status          TEXT DEFAULT 'scheduled',  -- scheduled | cancelled | completed | rescheduled
    service         TEXT,
    provider        TEXT,                      -- doctor, staff, etc.
    scheduled_at    TIMESTAMPTZ,
    duration_min    INTEGER DEFAULT 30,
    notes           TEXT,
    reminders       JSONB DEFAULT '[]',        -- [{type: 'sms', sent: false}]
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- AUDIT LOG (every agent action)
-- ============================================================
CREATE TABLE IF NOT EXISTS audit_logs (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id   UUID REFERENCES sessions(id),
    business_id  UUID REFERENCES businesses(id),
    log_level    TEXT DEFAULT 'INFO',          -- DEBUG | INFO | WARNING | ERROR
    event_type   TEXT,                         -- tool_call | llm_request | db_write | rag_retrieval | error
    tool_name    TEXT,
    input_data   JSONB,
    output_data  JSONB,
    rag_chunks   JSONB,                        -- retrieved chunks with scores
    duration_ms  INTEGER,
    error_msg    TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- CONVERSATION MESSAGES
-- ============================================================
CREATE TABLE IF NOT EXISTS messages (
    id           UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    session_id   UUID REFERENCES sessions(id),
    role         TEXT NOT NULL,                -- user | assistant | tool
    content      TEXT NOT NULL,
    tool_name    TEXT,
    tool_input   JSONB,
    tool_output  JSONB,
    created_at   TIMESTAMPTZ DEFAULT NOW()
);

-- ============================================================
-- INDEXES
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_sessions_business ON sessions(business_id);
CREATE INDEX IF NOT EXISTS idx_orders_session ON orders(session_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_appointments_session ON appointments(session_id);
CREATE INDEX IF NOT EXISTS idx_appointments_scheduled ON appointments(scheduled_at);
CREATE INDEX IF NOT EXISTS idx_audit_session ON audit_logs(session_id);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_messages_session ON messages(session_id);

-- ============================================================
-- UPDATED_AT auto-trigger
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_businesses_updated BEFORE UPDATE ON businesses
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_sessions_updated BEFORE UPDATE ON sessions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_orders_updated BEFORE UPDATE ON orders
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER trg_appointments_updated BEFORE UPDATE ON appointments
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
