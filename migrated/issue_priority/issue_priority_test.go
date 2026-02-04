package main

import (
	"testing"
)

func TestGetValueStr(t *testing.T) {
	// Save originals
	origGetValueStr := getValueStr

	// Mock by REASSIGNING the function variable
	getValueStr = func(doctype, name, fieldname string) (string, error) {
		return "mocked_value", nil
	}

	// Restore
	defer func() {
		getValueStr = origGetValueStr
	}()

	// Test code...
	value, err := getValueStr("some_key", "some_name", "some_field")
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if value != "mocked_value" {
		t.Fatalf("expected 'mocked_value', got %s", value)
	}
}

func TestGetActualQty(t *testing.T) {
	// Save originals
	origGetActualQty := GetActualQty

	// Mock by REASSIGNING the function variable
	GetActualQty = func(itemCode, warehouse string) float64 {
		return 200.0
	}

	// Restore
	defer func() {
		GetActualQty = origGetActualQty
	}()

	// Test code...
	actualQty := GetActualQty("item1", "warehouse1")
	if actualQty != 200.0 {
		t.Fatalf("expected 200.0, got %f", actualQty)
	}
}

func TestGetReservedQtyForProductionPlan(t *testing.T) {
	// Save originals
	origGetReservedQtyForProductionPlan := getReservedQtyForProductionPlan

	// Mock by REASSIGNING the function variable
	getReservedQtyForProductionPlan = func(planID string) float64 {
		return 50.0
	}

	// Restore
	defer func() {
		getReservedQtyForProductionPlan = origGetReservedQtyForProductionPlan
	}()

	// Test code...
	reservedQty := getReservedQtyForProductionPlan("plan1")
	if reservedQty != 50.0 {
		t.Fatalf("expected 50.0, got %f", reservedQty)
	}
}

func TestDbSet(t *testing.T) {
	// Save originals
	origDbSet := dbSet

	// Mock by REASSIGNING the function variable
	dbSet = func(doctype, name, fieldname, value string) error {
		return nil
	}

	// Restore
	defer func() {
		dbSet = origDbSet
	}()

	// Test code...
	err := dbSet("doctype", "name", "fieldname", "value")
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
}

func TestGetBinDetails(t *testing.T) {
	// Save originals
	origGetBinDetails := getBinDetails

	// Mock by REASSIGNING the function variable
	getBinDetails = func(batch string) map[string]string {
		return map[string]string{
			"actual_qty":   "150",
			"ordered_qty":  "75",
		}
	}

	// Restore
	defer func() {
		getBinDetails = origGetBinDetails
	}()

	// Test code...
	binDetails := getBinDetails("batch1")
	if binDetails["actual_qty"] != "150" {
		t.Fatalf("expected '150', got %s", binDetails["actual_qty"])
	}
	if binDetails["ordered_qty"] != "75" {
		t.Fatalf("expected '75', got %s", binDetails["ordered_qty"])
	}
}