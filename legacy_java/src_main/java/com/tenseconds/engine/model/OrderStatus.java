package com.tenseconds.engine.model;

/**
 * Lifecycle states of an order through the cloud kitchen pipeline.
 */
public enum OrderStatus {
    RECEIVED,
    ROUTED,
    QUEUED,
    SCHEDULED,
    PREPARING,
    READY,
    DISPATCHED,
    DELIVERED,
    CANCELLED
}
