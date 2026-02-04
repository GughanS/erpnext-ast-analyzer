package main

import (
	"testing"
)

func TestGetMonths(t *testing.T) {
	// Save originals
	origFlt := flt

	// Mock by REASSIGNING the function variable (not calling it)
	flt = func(val string) float64 {
		return 100.0
	}

	// Restore
	defer func() {
		flt = origFlt
	}()

	md := &MonthlyDistribution{}
	md.GetMonths()

	if len(md.Percentages) != 12 {
		t.Errorf("Expected 12 months, got %d", len(md.Percentages))
	}

	for i, month := range md.Percentages {
		if *month.Month != []string{"January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"}[i] {
			t.Errorf("Expected month %s, got %s", []string{"January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"}[i], *month.Month)
		}
		if *month.PercentageAllocation != 8.333333333333334 {
			t.Errorf("Expected percentage allocation 8.33, got %f", *month.PercentageAllocation)
		}
	}
}

func TestValidate(t *testing.T) {
	// Save originals
	origFlt := flt

	// Mock by REASSIGNING the function variable (not calling it)
	flt = func(val string) float64 {
		return 100.0
	}

	// Restore
	defer func() {
		flt = origFlt
	}()

	md := &MonthlyDistribution{}
	md.GetMonths()

	// Test valid allocation
	if err := md.Validate(); err != nil {
		t.Errorf("Expected no error, got %v", err)
	}

	// Test invalid allocation
	md.Percentages[0].PercentageAllocation = new(float64)
	if err := md.Validate(); err == nil {
		t.Error("Expected error, got none")
	}
}

func TestGetPercentage(t *testing.T) {
	// Save originals
	origAddMonths := addMonths

	// Mock by REASSIGNING the function variable (not calling it)
	addMonths = func(date string, months int) string {
		return "February" // Mocking to always return February for simplicity
	}

	// Restore
	defer func() {
		addMonths = origAddMonths
	}()

	md := &MonthlyDistribution{}
	md.GetMonths()

	percentage := GetPercentage(md, "January", 12)

	if percentage != 100.0 {
		t.Errorf("Expected percentage 100.0, got %f", percentage)
	}
}

func TestGetPeriodwiseDistributionData(t *testing.T) {
	// Save originals
	origGetPercentage := GetPercentage

	// Mock by REASSIGNING the function variable (not calling it)
	GetPercentage = func(doc *MonthlyDistribution, startDate string, period int) float64 {
		return 50.0 // Mocking to return a fixed percentage
	}

	// Restore
	defer func() {
		GetPercentage = origGetPercentage
	}()

	periodList := []Period{
		{Key: "Period1", FromDate: "January"},
		{Key: "Period2", FromDate: "February"},
	}

	result := GetPeriodwiseDistributionData("distributionID", periodList, "Monthly")

	if len(result) != 2 {
		t.Errorf("Expected 2 periods, got %d", len(result))
	}

	if result["Period1"] != 50.0 {
		t.Errorf("Expected percentage for Period1 to be 50.0, got %f", result["Period1"])
	}

	if result["Period2"] != 50.0 {
		t.Errorf("Expected percentage for Period2 to be 50.0, got %f", result["Period2"])
	}
}