package main

import (
	"fmt"
	"strings"
)

// --- MANDATORY ERROR PATTERN ---

type ValidationError struct {
	Message string
	Code    int
	Err     error
}

func (e *ValidationError) Error() string { return e.Message }
func (e *ValidationError) Unwrap() error { return e.Err }

// --- DATA STRUCTURES ---

// ModeofPaymentAccount represents a linked account entry within the MOP document.
type ModeofPaymentAccount struct {
	Company        string
	DefaultAccount string // The ledger account name
}

// ModeofPayment represents the core document structure relevant to validation.
type ModeofPayment struct {
	ModeOfPaymentName string
	Enabled           bool
	Accounts          []ModeofPaymentAccount
}

// --- DEPENDENCY INTERFACES (Frappe/DB Service Abstraction) ---

// DBService handles interactions typically done via frappe.db or frappe.get_cached_value.
type DBService interface {
	// GetAccountCompany retrieves the company associated with a specific Account ledger.
	GetAccountCompany(accountName string) (string, error)

	// CheckPOSUsage checks if the given Mode of Payment is referenced by any active POS Profile.
	// Returns a list of POS profile names if found.
	CheckPOSUsage(mopName string) ([]string, error)
}

// --- BUSINESS LOGIC IMPLEMENTATION (ModeofPayment) ---

// validateRepeatingCompanies ensures that no company is linked multiple times.
// Corresponds to Python: ModeofPayment.validate_repeating_companies
func validateRepeatingCompanies(mop *ModeofPayment) error {
	seen := make(map[string]struct{})
	for _, entry := range mop.Accounts {
		if _, found := seen[entry.Company]; found {
			return &ValidationError{
				Message: "Same Company is entered more than once",
				Code:    409,
			}
		}
		seen[entry.Company] = struct{}{}
	}
	return nil
}

// validateAccounts ensures that the Company specified in the MOPA entry matches the Company
// linked to the DefaultAccount ledger.
// Corresponds to Python: ModeofPayment.validate_accounts
func validateAccounts(mop *ModeofPayment, db DBService) error {
	for _, entry := range mop.Accounts {
		// Equivalent to frappe.get_cached_value("Account", entry.default_account, "company")
		ledgerCompany, err := db.GetAccountCompany(entry.DefaultAccount)
		if err != nil {
			// Wrap underlying internal DB error
			return fmt.Errorf("modeofpayment validation: failed to retrieve company for account %s: %w", entry.DefaultAccount, err)
		}

		if ledgerCompany != entry.Company {
			msg := fmt.Sprintf("Account %s does not match with Company %s in Mode of Account: %s",
				entry.DefaultAccount, entry.Company, mop.ModeOfPaymentName)

			return &ValidationError{
				Message: msg,
				Code:    400,
			}
		}
	}
	return nil
}

// validatePOSModeOfPayment prevents disabling the MOP if it is used in active POS profiles.
// Corresponds to Python: ModeofPayment.validate_pos_mode_of_payment
func validatePOSModeOfPayment(mop *ModeofPayment, db DBService) error {
	if mop.Enabled {
		return nil // Only validate usage restriction if attempting to disable
	}

	// Equivalent to SQL query fetching POS Profiles
	posProfiles, err := db.CheckPOSUsage(mop.ModeOfPaymentName)
	if err != nil {
		return fmt.Errorf("modeofpayment validation: failed to check POS usage for MOP %s: %w", mop.ModeOfPaymentName, err)
	}

	if len(posProfiles) > 0 {
		profileList := strings.Join(posProfiles, ", ")

		message := fmt.Sprintf(
			"POS Profile %s contains Mode of Payment %s. Please remove them to disable this mode.",
			profileList,
			mop.ModeOfPaymentName,
		)

		return &ValidationError{
			Message: message,
			Code:    403, // Not Allowed
		}
	}
	return nil
}

// --- ARCHITECTURAL SERVICE ---

// ModeofPaymentService orchestrates the document validation process.
type ModeofPaymentService struct {
	DB DBService
}

// Validate executes all business rule checks defined for the ModeofPayment document.
func (v *ModeofPaymentService) Validate(mop *ModeofPayment) error {
	// 1. Validate repeating companies
	if err := validateRepeatingCompanies(mop); err != nil {
		return err
	}

	// 2. Validate accounts/company consistency
	if err := validateAccounts(mop, v.DB); err != nil {
		return err
	}

	// 3. Validate POS usage (if disabling)
	if err := validatePOSModeOfPayment(mop, v.DB); err != nil {
		return err
	}

	return nil
}