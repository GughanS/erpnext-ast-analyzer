package main

import (
	"testing"
)

func TestRecalculateQty(t *testing.T) {
	// Save originals
	origGetActualQty := GetActualQty
	origGetReservedQtyForProductionPlan := getReservedQtyForProductionPlan
	origDbSet := dbSet

	// Mock by REASSIGNING the function variable (not calling it)
	GetActualQty = func(itemCode, warehouse string) float64 {
		return 100.0
	}

	getReservedQtyForProductionPlan = func(productionPlan, item string) float64 {
		return 50.0
	}

	dbSet = func(doctype, name, fieldname, value string) error {
		return nil
	}

	// Restore
	defer func() {
		GetActualQty = origGetActualQty
		getReservedQtyForProductionPlan = origGetReservedQtyForProductionPlan
		dbSet = origDbSet
	}()

	bin := &Bin{
		Item:                             stringPtr("item1"),
		Warehouse:                        stringPtr("warehouse1"),
		ActualQty:                        float64Ptr(0),
		PlannedQty:                       float64Ptr(0),
		IndentedQty:                      float64Ptr(0),
		OrderedQty:                       float64Ptr(0),
		ReservedQty:                      float64Ptr(0),
		ReservedQtyForProduction:         float64Ptr(0),
		ReservedQtyForProductionPlan:     float64Ptr(0),
		isNew:                            true,
	}

	bin.recalculateQty()

	if *bin.ActualQty != 100.0 {
		t.Errorf("Expected ActualQty to be 100.0, got %f", *bin.ActualQty)
	}
	if *bin.ReservedQtyForProductionPlan != 50.0 {
		t.Errorf("Expected ReservedQtyForProductionPlan to be 50.0, got %f", *bin.ReservedQtyForProductionPlan)
	}
}

func TestBeforeSave(t *testing.T) {
	// Save originals
	origGetValueStr := getValueStr
	origDbSet := dbSet

	// Mock by REASSIGNING the function variable (not calling it)
	getValueStr = func(doctype, name, fieldname string) (string, error) {
		return "pcs", nil
	}

	dbSet = func(doctype, name, fieldname, value string) error {
		return nil
	}

	// Restore
	defer func() {
		getValueStr = origGetValueStr
		dbSet = origDbSet
	}()

	bin := &Bin{
		Item:     stringPtr("item1"),
		Warehouse: stringPtr("warehouse1"),
		isNew:    true,
	}

	bin.beforeSave()

	if *bin.StockUOM != "pcs" {
		t.Errorf("Expected StockUOM to be 'pcs', got %s", *bin.StockUOM)
	}
}

func TestUpdateQty(t *testing.T) {
	// Save originals
	origGetBinDetails := getBinDetails
	origGetActualQty := GetActualQty
	origDbSet := dbSet

	// Mock by REASSIGNING the function variable (not calling it)
	getBinDetails = func(batch string) map[string]string {
		return map[string]string{
			"actual_qty":              "100",
			"ordered_qty":             "50",
			"reserved_qty":            "20",
			"indented_qty":            "30",
			"planned_qty":             "40",
			"reserved_qty_for_production": "10",
			"reserved_qty_for_sub_contract": "5",
			"reserved_qty_for_production_plan": "15",
		}
	}

	GetActualQty = func(itemCode, warehouse string) float64 {
		return 120.0
	}

	dbSet = func(doctype, name, fieldname, value string) error {
		return nil
	}

	// Restore
	defer func() {
		getBinDetails = origGetBinDetails
		GetActualQty = origGetActualQty
		dbSet = origDbSet
	}()

	args := map[string]interface{}{
		"item_code":     "item1",
		"warehouse":     "warehouse1",
		"ordered_qty":   "10",
		"reserved_qty":  "5",
		"indented_qty":  "5",
		"planned_qty":   "5",
	}

	updateQty("bin1", args)

	// You can add assertions here to verify the expected behavior
}
  
func stringPtr(s string) *string {
	return &s
}

func float64Ptr(f float64) *float64 {
	return &f
}