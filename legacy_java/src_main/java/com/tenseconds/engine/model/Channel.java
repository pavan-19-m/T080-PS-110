package com.tenseconds.engine.model;

/**
 * Ordering channels and their specific commission structures (BR-09).
 */
public enum Channel {
    AGGREGATOR_A(0.22, 0.0),
    AGGREGATOR_B(0.18, 0.0),
    OWN_APP(0.00, 15.0);

    private final double commissionRate;
    private final double fixedFee;

    Channel(double commissionRate, double fixedFee) {
        this.commissionRate = commissionRate;
        this.fixedFee = fixedFee;
    }

    public double getCommissionRate() {
        return commissionRate;
    }

    public double getFixedFee() {
        return fixedFee;
    }

    public static Channel fromString(String text) {
        if (text == null) {
            throw new IllegalArgumentException("Channel cannot be null");
        }
        String clean = text.trim().toUpperCase().replace(" ", "_").replace("-", "_");
        switch (clean) {
            case "AGGREGATOR_A":
            case "AGGREGATORA":
                return AGGREGATOR_A;
            case "AGGREGATOR_B":
            case "AGGREGATORB":
                return AGGREGATOR_B;
            case "OWN_APP":
            case "OWNAPP":
            case "APP":
                return OWN_APP;
            default:
                throw new IllegalArgumentException("Unknown channel: " + text);
        }
    }
}
