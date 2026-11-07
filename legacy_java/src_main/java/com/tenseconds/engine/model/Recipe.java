package com.tenseconds.engine.model;

import java.util.Objects;

/**
 * Cooking recipe mapping to a station, preparation time, batch limit, and optional predecessor dependency.
 */
public class Recipe {
    private final String recipeId;
    private final StationType stationType;
    private final int prepMinutes;
    private final int maxBatchSize;
    private final String dependencyRecipeId; // Recipe that must finish before this one can start

    public Recipe(String recipeId, StationType stationType, int prepMinutes, int maxBatchSize, String dependencyRecipeId) {
        this.recipeId = Objects.requireNonNull(recipeId, "recipeId cannot be null").trim();
        this.stationType = Objects.requireNonNull(stationType, "stationType cannot be null");
        if (prepMinutes <= 0) {
            throw new IllegalArgumentException("prepMinutes must be positive, got: " + prepMinutes);
        }
        if (maxBatchSize <= 0) {
            throw new IllegalArgumentException("maxBatchSize must be positive, got: " + maxBatchSize);
        }
        this.prepMinutes = prepMinutes;
        this.maxBatchSize = maxBatchSize;
        this.dependencyRecipeId = (dependencyRecipeId != null && !dependencyRecipeId.trim().isEmpty()) 
                ? dependencyRecipeId.trim() 
                : null;
    }

    public String getRecipeId() {
        return recipeId;
    }

    public StationType getStationType() {
        return stationType;
    }

    public int getPrepMinutes() {
        return prepMinutes;
    }

    public int getMaxBatchSize() {
        return maxBatchSize;
    }

    public String getDependencyRecipeId() {
        return dependencyRecipeId;
    }

    public boolean hasDependency() {
        return dependencyRecipeId != null;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Recipe recipe = (Recipe) o;
        return recipeId.equals(recipe.recipeId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(recipeId);
    }

    @Override
    public String toString() {
        return "Recipe{" +
                "recipeId='" + recipeId + '\'' +
                ", stationType=" + stationType +
                ", prepMinutes=" + prepMinutes +
                ", maxBatchSize=" + maxBatchSize +
                ", dependencyRecipeId='" + dependencyRecipeId + '\'' +
                '}';
    }
}
