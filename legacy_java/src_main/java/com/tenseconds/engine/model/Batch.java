package com.tenseconds.engine.model;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.Objects;

/**
 * A cooking batch combining identical recipes on the same station into one slot (BR-02).
 */
public class Batch {
    private final String batchId;
    private final String recipeId;
    private final StationType stationType;
    private final int maxBatchSize;
    private LocalDateTime startTime;
    private LocalDateTime endTime;
    private final List<OrderItem> items = new ArrayList<>();

    public Batch(String batchId, String recipeId, StationType stationType, int maxBatchSize) {
        this.batchId = Objects.requireNonNull(batchId, "batchId cannot be null").trim();
        this.recipeId = Objects.requireNonNull(recipeId, "recipeId cannot be null").trim();
        this.stationType = Objects.requireNonNull(stationType, "stationType cannot be null");
        this.maxBatchSize = maxBatchSize;
    }

    public String getBatchId() {
        return batchId;
    }

    public String getRecipeId() {
        return recipeId;
    }

    public StationType getStationType() {
        return stationType;
    }

    public int getMaxBatchSize() {
        return maxBatchSize;
    }

    public LocalDateTime getStartTime() {
        return startTime;
    }

    public void setStartTime(LocalDateTime startTime) {
        this.startTime = startTime;
    }

    public LocalDateTime getEndTime() {
        return endTime;
    }

    public void setEndTime(LocalDateTime endTime) {
        this.endTime = endTime;
    }

    public List<OrderItem> getItems() {
        return Collections.unmodifiableList(items);
    }

    public boolean canAddItem() {
        return items.size() < maxBatchSize;
    }

    public boolean addItem(OrderItem item) {
        if (!canAddItem()) {
            return false;
        }
        items.add(item);
        item.setBatchId(this.batchId);
        return true;
    }

    public int getCurrentSize() {
        return items.size();
    }

    @Override
    public String toString() {
        return "Batch{" +
                "batchId='" + batchId + '\'' +
                ", recipeId='" + recipeId + '\'' +
                ", stationType=" + stationType +
                ", currentSize=" + items.size() +
                "/" + maxBatchSize +
                ", startTime=" + startTime +
                ", endTime=" + endTime +
                '}';
    }
}
