CREATE TABLE IF NOT EXISTS transactions (
    txn_id UUID PRIMARY KEY,
    user_id VARCHAR(255) NOT NULL,
    amount NUMERIC(12, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL,
    merchant_id VARCHAR(255) NOT NULL,
    mcc VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL,
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    device_fingerprint VARCHAR(255),
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS decisions (
    txn_id UUID PRIMARY KEY REFERENCES transactions(txn_id),
    risk_score NUMERIC(5, 4) NOT NULL,
    decision VARCHAR(10) NOT NULL CHECK (decision IN ('APPROVE', 'HOLD', 'BLOCK')),
    breakdown_json JSONB NOT NULL DEFAULT '[]',
    rules_triggered TEXT[] DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    condition_json JSONB NOT NULL,
    action VARCHAR(10) NOT NULL CHECK (action IN ('BLOCK', 'HOLD')),
    priority INTEGER DEFAULT 0,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS chargebacks (
    chargeback_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    txn_id UUID NOT NULL REFERENCES transactions(txn_id),
    reason TEXT NOT NULL,
    reported_at TIMESTAMPTZ DEFAULT NOW(),
    processed_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS scoring_weights (
    category VARCHAR(50) PRIMARY KEY,
    weight NUMERIC(5, 4) NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Seed default weights
INSERT INTO scoring_weights (category, weight) VALUES
    ('velocity', 0.3), ('geo', 0.2), ('device', 0.3), ('graph', 0.2)
ON CONFLICT (category) DO NOTHING;

-- Seed default rules
INSERT INTO rules (name, condition_json, action, priority) VALUES
    ('high_amount_first_txn', '{"amount_gt": 10000, "is_first_transaction": true}', 'BLOCK', 100),
    ('impossible_travel', '{"geo_velocity_kmh_gt": 900}', 'BLOCK', 90),
    ('shared_devices', '{"shared_device_count_gt": 5}', 'HOLD', 80)
ON CONFLICT DO NOTHING;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_decisions_created_at ON decisions(created_at);
CREATE INDEX IF NOT EXISTS idx_chargebacks_txn_id ON chargebacks(txn_id);
CREATE INDEX IF NOT EXISTS idx_transactions_user_id ON transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_transactions_timestamp ON transactions(timestamp);
