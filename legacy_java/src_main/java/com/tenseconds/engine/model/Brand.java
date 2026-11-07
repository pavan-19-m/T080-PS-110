package com.tenseconds.engine.model;

import java.util.Collections;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;

/**
 * Virtual restaurant brand operating in cloud kitchens.
 */
public class Brand {
    private final String brandId;
    private final String name;
    private final Map<String, MenuItem> menuItems;

    public Brand(String brandId, String name) {
        this(brandId, name, Collections.emptyMap());
    }

    public Brand(String brandId, String name, Map<String, MenuItem> menuItems) {
        this.brandId = Objects.requireNonNull(brandId, "brandId cannot be null").trim();
        this.name = Objects.requireNonNull(name, "name cannot be null").trim();
        this.menuItems = new HashMap<>(menuItems);
    }

    public String getBrandId() {
        return brandId;
    }

    public String getName() {
        return name;
    }

    public Map<String, MenuItem> getMenuItems() {
        return Collections.unmodifiableMap(menuItems);
    }

    public void addMenuItem(MenuItem item) {
        Objects.requireNonNull(item, "item cannot be null");
        menuItems.put(item.getItemId(), item);
    }

    public MenuItem getMenuItem(String itemId) {
        return menuItems.get(itemId);
    }

    public boolean hasMenuItem(String itemId) {
        return menuItems.containsKey(itemId);
    }

    @Override
    public boolean equals(Object o) {
        if (this == o) return true;
        if (o == null || getClass() != o.getClass()) return false;
        Brand brand = (Brand) o;
        return brandId.equals(brand.brandId);
    }

    @Override
    public int hashCode() {
        return Objects.hash(brandId);
    }

    @Override
    public String toString() {
        return "Brand{" +
                "brandId='" + brandId + '\'' +
                ", name='" + name + '\'' +
                ", itemCount=" + menuItems.size() +
                '}';
    }
}
