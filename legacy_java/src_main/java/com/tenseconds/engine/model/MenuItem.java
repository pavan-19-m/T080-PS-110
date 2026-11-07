package com.tenseconds.engine.model;

import java.util.Objects;

/**
 * Menu item belonging to a brand, with a retail price and mapped recipe.
 */
public class MenuItem {
    private final String itemId;
    private final String brandId;
    private final String name;
    private final double price;
    private final String recipeId;

    public MenuItem(String itemId, String brandId, String name, double price, String recipeId) {
        this.itemId = Objects.requireNonNull(itemId, "itemId cannot be null").trim();
        this.brandId = Objects.requireNonNull(brandId, "brandId cannot be null").trim();
        this.name = Objects.requireNonNull(name, "name cannot be null").trim();
        if (price < 0) {
            throw new IllegalArgumentException("price cannot be negative, got: " + price);
        }
        this.price = price;
        this.recipeId = Objects.requireNonNull(recipeId, "recipeId cannot be null").trim();
    }

    public String getItemId() {
        return itemId;
    }

    public String getBrandId() {
        return brandId;
    }

    public String getName() {
        return name;
    }

    public double getPrice() {
        return price;
    }

    public String getRecipeId() {
        return recipeId;
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        MenuItem menuItem = (MenuItem) o;
        return itemId.equals(menuItem.itemId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(itemId);
    }

    @Override
    public String toString() {
        return "MenuItem{" +
                "itemId='" + itemId + '\'' +
                ", brandId='" + brandId + '\'' +
                ", name='" + name + '\'' +
                ", price=" + price +
                ", recipeId='" + recipeId + '\'' +
                '}';
    }
}
