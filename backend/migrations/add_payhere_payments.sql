
-- PayHere Sandbox Payment Tracking
-- Additive migration: existing bookings and hotels remain unchanged.

CREATE TABLE IF NOT EXISTS payments (
    id BIGSERIAL PRIMARY KEY,

    booking_id INTEGER NOT NULL
        REFERENCES bookings(id) ON DELETE RESTRICT,

    order_id VARCHAR(100) NOT NULL UNIQUE,

    provider VARCHAR(30) NOT NULL DEFAULT 'payhere',

    amount NUMERIC(12, 2) NOT NULL
        CHECK (amount > 0),

    currency VARCHAR(3) NOT NULL DEFAULT 'LKR',

    status VARCHAR(30) NOT NULL DEFAULT 'pending',

    payhere_payment_id VARCHAR(100) UNIQUE,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT payments_status_check
        CHECK (status IN ('pending', 'success', 'failed', 'cancelled'))
);

CREATE INDEX IF NOT EXISTS idx_payments_booking_id
ON payments (booking_id);
