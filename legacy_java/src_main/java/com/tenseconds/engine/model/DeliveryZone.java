package com.tenseconds.engine.model;

import java.util.Collections;
import java.util.HashSet;
import java.util.Objects;
import java.util.Set;

/**
 * Geographic delivery zone with delivery transit minutes and eligible kitchens.
 */
public class DeliveryZone {
    private final String zoneId;
    private final int deliveryMinutes;
    private final Set<String> eligibleKitchenIds;

    public DeliveryZone(String zoneId, int deliveryMinutes, Set<String> eligibleKitchenIds) {
        this.zoneId = Objects.requireNonNull(zoneId, "zoneId cannot be null").trim();
        this.deliveryMinutes = deliveryMinutes;
        this.eligibleKitchenIds = eligibleKitchenIds != null 
                ? Collections.unmodifiableSet(new HashSet<>(eligibleKitchenIds)) 
                : Collections.emptySet();
    }

    public String getZoneId() {
        return zoneId;
    }

    public int getDeliveryMinutes() {
        return deliveryMinutes;
    }

    public Set<String> getEligibleKitchenIds() {
        return eligibleKitchenIds;
    }

    public boolean servesKitchen(String kitchenId) {
        return kitchenId != null && eligibleKitchenIds.contains(kitchenId.trim());
    }

    @Override
    public String toString() {
        return "DeliveryZone{" +
                "zoneId='" + zoneId + '\'' +
                ", deliveryMinutes=" + deliveryMinutes +
                ", eligibleKitchenIds=" + eligibleKitchenIds +
                '}';
    }
}
