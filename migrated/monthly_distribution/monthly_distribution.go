package main

import (
	"errors"
	"fmt"
)

type MonthlyDistribution struct {
	DistributionID string
	FiscalYear     *string
	Percentages    []MonthlyDistributionPercentage
}

type MonthlyDistributionPercentage struct {
	Month               *string
	PercentageAllocation *float64
	Idx                 int
}

var getValueStr = func(doctype, name, fieldname string) (string, error) {
	// Implementation here
	return "", nil
}

var flt = func(val string) float64 {
	// Implementation here
	return 0.0
}

var addMonths = func(date string, months int) string {
	// Implementation here
	return ""
}

func (md *MonthlyDistribution) GetMonths() {
	monthList := []string{
		"January",
		"February",
		"March",
		"April",
		"May",
		"June",
		"July",
		"August",
		"September",
		"October",
		"November",
		"December",
	}
	idx := 1
	for _, m := range monthList {
		mnth := MonthlyDistributionPercentage{}
		mnth.Month = &m
		allocation := 100.0 / 12
		mnth.PercentageAllocation = &allocation
		mnth.Idx = idx
		md.Percentages = append(md.Percentages, mnth)
		idx++
	}
}

func (md *MonthlyDistribution) Validate() error {
	total := 0.0
	for _, d := range md.Percentages {
		total += *d.PercentageAllocation
	}

	if flt(fmt.Sprintf("%.2f", total)) != 100.0 {
		return errors.New(fmt.Sprintf("Percentage Allocation should be equal to 100%% (%s%%)", fmt.Sprintf("%.2f", total)))
	}
	return nil
}

func GetPeriodwiseDistributionData(distributionID string, periodList []Period, periodicity string) map[string]float64 {
	doc := MonthlyDistribution{} // Assume we fetch the document here

	monthsToAdd := map[string]int{
		"Yearly":    12,
		"Half-Yearly": 6,
		"Quarterly": 3,
		"Monthly":   1,
	}[periodicity]

	periodDict := make(map[string]float64)

	for _, d := range periodList {
		periodDict[d.Key] = GetPercentage(&doc, d.FromDate, monthsToAdd)
	}

	return periodDict
}

func GetPercentage(doc *MonthlyDistribution, startDate string, period int) float64 {
	percentage := 0.0
	months := []string{startDate} // Assume startDate is formatted to month name

	for r := 1; r < period; r++ {
		months = append(months, addMonths(startDate, r))
	}

	for _, d := range doc.Percentages {
		if *d.Month != "" {
			for _, month := range months {
				if *d.Month == month {
					percentage += *d.PercentageAllocation
				}
			}
		}
	}

	return percentage
}

type Period struct {
	Key      string
	FromDate string
}