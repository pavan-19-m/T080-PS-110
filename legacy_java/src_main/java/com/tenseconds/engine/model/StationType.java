package com.tenseconds.engine.model;

/**
 * Represents the distinct culinary preparation station types inside a cloud kitchen.
 */
public enum StationType {
    GRILL,
    FRYER,
    WOK,
    COLD,
    BAKERY;

    public static StationType fromString(String text) {
        if (text == null) {
            throw new IllegalArgumentException("StationType cannot be null");
        }
        return StationType.valueOf(text.trim().toUpperCase());
    }
}
