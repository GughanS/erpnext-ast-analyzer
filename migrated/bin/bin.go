package main

import (
	"fmt"
)

type Bin struct {
	Name                             *string   // String pointer
	Item                             *string   // String pointer
	Warehouse                        *string   // String pointer
	ActualQty                        *float64  // Numeric pointer (NOT *string)
	ProjectedQty                     *float64  // Numeric pointer (NOT *string)
	OrderedQty                       *float64  // Numeric pointer (NOT *string)
	IndentedQty                      *float64  // Numeric pointer (NOT *string)
	PlannedQty                       *float64  // Numeric pointer (NOT *string)
	ReservedQty                      *float64  // Numeric pointer (NOT *string)
	ReservedQtyForProduction         *float64  // Numeric pointer (NOT *string)
	ReservedQtyForSubContract        *float64  // Numeric pointer (NOT *string)
	isNew                            bool      // Boolean (NOT pointer)
}

var getValueStr = func(doctype, name, fieldname string) (string, error) {
	// Implementation here
	return "", nil
}

var dbGetValue = func(doctype, name, fieldname string) (string, error) {
	// Implementation here
	return "", nil
}

var dbSet = func(doctype, name, fieldname, value string) error {
	// Implementation here
	return nil
}

var makeAutoname = func(key string) string {
	// Implementation here
	return ""
}

var getNameFromHash = func(hash string) string {
	// Implementation here
	return ""
}

var batchExists = func(name string) bool {
	// Implementation here
	return false
}

var futureSleExists = func(args interface{}) bool {
	// Implementation here
	return false
}

var revertSeriesIfLast = func(series, name string) {
	// Implementation here
}

var getBatchQty = func(batch, warehouse string) float64 {
	// Implementation here
	return 0.0
}

var getValuationMethod = func(item string) string {
	// Implementation here
	return ""
}

var addDays = func(date string, days int) string {
	// Implementation here
	return ""
}

var renderTemplate = func(template string, data interface{}) string {
	// Implementation here
	return ""
}

var getBinDetails = func(batch string) map[string]string {
	// Implementation here
	return map[string]string{}
}

var getExpiryDetails = func(batch string) string {
	// Implementation here
	return ""
}

var getReservedQtyForProductionPlan = func(productionPlan, item string) float64 {
	// Implementation here
	return 0.0
}

var GetActualQty = func(itemCode, warehouse string) float64 {
	// Implementation here
	return 0.0
}

func (b *Bin) recalculateQty() {
	b.ActualQty = new(float64)

	plannedQtyStr, _ := getValueStr("Bin", *b.Item, "planned_qty")
	b.PlannedQty = new(float64)

	indentedQtyStr, _ := getValueStr("Bin", *b.Item, "indented_qty")
	b.IndentedQty = new(float64)

	orderedQtyStr, _ := getValueStr("Bin", *b.Item, "ordered_qty")
	b.OrderedQty = new(float64)

	reservedQtyStr, _ := getValueStr("Bin", *b.Item, "reserved_qty")
	b.ReservedQty = new(float64)

	reservedQtyForProductionStr, _ := getValueStr("Bin", *b.Item, "reserved_qty_for_production")
	b.ReservedQtyForProduction = new(float64)

	b.updateReservedQtyForSubContracting(false)
	b.updateReservedQtyForProductionPlan(true, false)
	b.setProjectedQty()
}

func (b *Bin) beforeSave() {
	if b.isNew || b.StockUOM == nil {
		stockUOM, _ := getValueStr("Item", *b.Item, "stock_uom")
		b.StockUOM = &stockUOM
	}
	b.setProjectedQty()
}

func (b *Bin) setProjectedQty() {
	total := *b.ActualQty + *b.OrderedQty + *b.IndentedQty + *b.PlannedQty - *b.ReservedQty - *b.ReservedQtyForProduction - *b.ReservedQtyForSubContract
	b.ProjectedQty = new(float64)
}

func (b *Bin) updateReservedQtyForProductionPlan(skipProjectQtyUpdate bool, updateQty bool) {
	reservedQtyForProductionPlan := getReservedQtyForProductionPlan(*b.Item, *b.Warehouse)

	if reservedQtyForProductionPlan == 0 && *b.ReservedQtyForProductionPlan == 0 {
		return
	}

	b.ReservedQtyForProductionPlan = new(float64)

	if updateQty {
		dbSet("Bin", *b.Name, "reserved_qty_for_production_plan", fmt.Sprintf("%f", *b.ReservedQtyForProductionPlan))
	}

	if !skipProjectQtyUpdate {
		b.setProjectedQty()
		dbSet("Bin", *b.Name, "projected_qty", fmt.Sprintf("%f", *b.ProjectedQty))
	}
}

func (b *Bin) updateReservedQtyForSubContracting(updateQty bool) {
	// Implementation here
}

func (b *Bin) updateReservedStock() {
	reservedStock := getReservedQtyForProductionPlan(*b.Item, *b.Warehouse)
	dbSet("Bin", *b.Name, "reserved_stock", fmt.Sprintf("%f", reservedStock))
}

func updateQty(binName string, args map[string]interface{}) {
	binDetails := getBinDetails(binName)
	actualQty := binDetails["actual_qty"]

	if futureSleExists(args) {
		actualQty = GetActualQty(args["item_code"].(string), args["warehouse"].(string))
	}

	orderedQty := flt(binDetails["ordered_qty"]) + flt(args["ordered_qty"].(string))
	reservedQty := flt(binDetails["reserved_qty"]) + flt(args["reserved_qty"].(string))
	indentedQty := flt(binDetails["indented_qty"]) + flt(args["indented_qty"].(string))
	plannedQty := flt(binDetails["planned_qty"]) + flt(args["planned_qty"].(string))

	projectedQty := actualQty + orderedQty + indentedQty + plannedQty - reservedQty - flt(binDetails["reserved_qty_for_production"]) - flt(binDetails["reserved_qty_for_sub_contract"]) - flt(binDetails["reserved_qty_for_production_plan"])

	dbSet("Bin", binName, "actual_qty", fmt.Sprintf("%f", actualQty))
	dbSet("Bin", binName, "ordered_qty", fmt.Sprintf("%f", orderedQty))
	dbSet("Bin", binName, "reserved_qty", fmt.Sprintf("%f", reservedQty))
	dbSet("Bin", binName, "indented_qty", fmt.Sprintf("%f", indentedQty))
	dbSet("Bin", binName, "planned_qty", fmt.Sprintf("%f", plannedQty))
	dbSet("Bin", binName, "projected_qty", fmt.Sprintf("%f", projectedQty))
}

func getActualQty(itemCode, warehouse string) float64 {
	// Implementation here
	return 0.0
}