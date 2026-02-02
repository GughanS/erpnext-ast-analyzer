package main

import (
	"errors"
	"fmt"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
)

// --- MOCK IMPLEMENTATION ---

// MockDBService is a mock implementation of DBService for testing.
type MockDBService struct {
	AccountCompanyMap    map[string]string
	POSUsage             map[string][]string
	ErrorOnAccountLookup error
	ErrorOnPOSCheck      error
}

func (m *MockDBService) GetAccountCompany(accountName string) (string, error) {
	if m.ErrorOnAccountLookup != nil {
		return "", m.ErrorOnAccountLookup
	}
	company, ok := m.AccountCompanyMap[accountName]
	if !ok {
		// Simulate a case where the account might not exist, but usually frappe handles this earlier.
		// Returning an error specific to the account lookup failure.
		return "", fmt.Errorf("account %s not found in mock cache", accountName)
	}
	return company, nil
}

func (m *MockDBService) CheckPOSUsage(mopName string) ([]string, error) {
	if m.ErrorOnPOSCheck != nil {
		return nil, m.ErrorOnPOSCheck
	}
	profiles, ok := m.POSUsage[mopName]
	if !ok {
		return []string{}, nil
	}
	return profiles, nil
}

// --- TEST SUITE ---

func TestValidateRepeatingCompanies(t *testing.T) {
	t.Run("Success_NoRepeats", func(t *testing.T) {
		mop := &ModeofPayment{
			Accounts: []ModeofPaymentAccount{
				{Company: "Company A"},
				{Company: "Company B"},
				{Company: "Company C"},
			},
		}
		assert.NoError(t, validateRepeatingCompanies(mop))
	})

	t.Run("Failure_CompanyRepeated", func(t *testing.T) {
		mop := &ModeofPayment{
			Accounts: []ModeofPaymentAccount{
				{Company: "Company X"},
				{Company: "Company Y"},
				{Company: "Company X"}, // Repeat
			},
		}
		err := validateRepeatingCompanies(mop)
		assert.Error(t, err)

		var vErr *ValidationError
		assert.True(t, errors.As(err, &vErr))
		assert.Equal(t, 409, vErr.Code)
		assert.Contains(t, vErr.Message, "Same Company is entered more than once")
	})

	t.Run("Success_EmptyList", func(t *testing.T) {
		mop := &ModeofPayment{Accounts: []ModeofPaymentAccount{}}
		assert.NoError(t, validateRepeatingCompanies(mop))
	})
}

func TestValidateAccounts(t *testing.T) {
	mockDB := &MockDBService{
		AccountCompanyMap: map[string]string{
			"ACC_USD": "US Corp",
			"ACC_EUR": "EU Corp",
		},
	}

	t.Run("Success_AllMatch", func(t *testing.T) {
		mop := &ModeofPayment{
			ModeOfPaymentName: "Wire",
			Accounts: []ModeofPaymentAccount{
				{Company: "US Corp", DefaultAccount: "ACC_USD"},
				{Company: "EU Corp", DefaultAccount: "ACC_EUR"},
			},
		}
		assert.NoError(t, validateAccounts(mop, mockDB))
	})

	t.Run("Failure_CompanyMismatch", func(t *testing.T) {
		mop := &ModeofPayment{
			ModeOfPaymentName: "MismatchMOP",
			Accounts: []ModeofPaymentAccount{
				{Company: "WRONG Corp", DefaultAccount: "ACC_USD"}, // ACC_USD belongs to US Corp
			},
		}
		err := validateAccounts(mop, mockDB)
		assert.Error(t, err)

		var vErr *ValidationError
		assert.True(t, errors.As(err, &vErr))
		assert.Equal(t, 400, vErr.Code)
		assert.Contains(t, vErr.Message, "Account ACC_USD does not match with Company WRONG Corp")
		assert.Contains(t, vErr.Message, "MismatchMOP")
	})

	t.Run("Failure_UnderlyingDBError", func(t *testing.T) {
		dbErr := errors.New("sql connection failure")
		mockDBWithError := &MockDBService{
			ErrorOnAccountLookup: dbErr,
		}
		mop := &ModeofPayment{
			Accounts: []ModeofPaymentAccount{{DefaultAccount: "SomeAccount"}},
		}

		err := validateAccounts(mop, mockDBWithError)
		assert.Error(t, err)
		
		// Check that the error is wrapped, but not a ValidationError
		var vErr *ValidationError
		assert.False(t, errors.As(err, &vErr))
		assert.True(t, errors.Is(err, dbErr))
		assert.True(t, strings.Contains(err.Error(), "failed to retrieve company for account SomeAccount"))
	})
}

func TestValidatePOSModeOfPayment(t *testing.T) {
	mopName := "GiftCard"
	
	t.Run("Success_MOPIsEnabled", func(t *testing.T) {
		mop := &ModeofPayment{ModeOfPaymentName: mopName, Enabled: true}
		mockDB := &MockDBService{
			POSUsage: map[string][]string{mopName: {"P1"}},
		}
		// Should succeed even if usage exists, because we are not disabling it.
		assert.NoError(t, validatePOSModeOfPayment(mop, mockDB))
	})

	t.Run("Success_DisabledButNoUsage", func(t *testing.T) {
		mop := &ModeofPayment{ModeOfPaymentName: mopName, Enabled: false}
		mockDB := &MockDBService{
			POSUsage: map[string][]string{mopName: {}},
		}
		assert.NoError(t, validatePOSModeOfPayment(mop, mockDB))
	})

	t.Run("Failure_DisabledWithSinglePOSUsage", func(t *testing.T) {
		mop := &ModeofPayment{ModeOfPaymentName: mopName, Enabled: false}
		mockDB := &MockDBService{
			POSUsage: map[string][]string{mopName: {"Profile A"}},
		}
		err := validatePOSModeOfPayment(mop, mockDB)
		assert.Error(t, err)

		var vErr *ValidationError
		assert.True(t, errors.As(err, &vErr))
		assert.Equal(t, 403, vErr.Code)
		assert.Contains(t, vErr.Message, "POS Profile Profile A contains Mode of Payment GiftCard")
	})

	t.Run("Failure_DisabledWithMultiplePOSUsage", func(t *testing.T) {
		mop := &ModeofPayment{ModeOfPaymentName: mopName, Enabled: false}
		mockDB := &MockDBService{
			POSUsage: map[string][]string{mopName: {"Profile X", "Profile Y", "Profile Z"}},
		}
		err := validatePOSModeOfPayment(mop, mockDB)
		assert.Error(t, err)

		var vErr *ValidationError
		assert.True(t, errors.As(err, &vErr))
		assert.Equal(t, 403, vErr.Code)
		assert.Contains(t, vErr.Message, "POS Profile Profile X, Profile Y, Profile Z contains Mode of Payment GiftCard")
	})

	t.Run("Failure_UnderlyingDBError", func(t *testing.T) {
		dbErr := errors.New("network timeout")
		mop := &ModeofPayment{ModeOfPaymentName: mopName, Enabled: false}
		mockDB := &MockDBService{
			ErrorOnPOSCheck: dbErr,
		}

		err := validatePOSModeOfPayment(mop, mockDB)
		assert.Error(t, err)
		
		var vErr *ValidationError
		assert.False(t, errors.As(err, &vErr))
		assert.True(t, errors.Is(err, dbErr))
		assert.Contains(t, err.Error(), "failed to check POS usage for MOP GiftCard")
	})
}

func TestModeofPaymentService_Validate(t *testing.T) {
	standardDB := &MockDBService{
		AccountCompanyMap: map[string]string{
			"ACC_OK_1": "C1",
			"ACC_OK_2": "C2",
		},
		POSUsage: map[string][]string{"MOP_ACTIVE": {}},
	}

	service := &ModeofPaymentService{DB: standardDB}

	// 1. Full Success Path
	t.Run("Integration_Success", func(t *testing.T) {
		mop := &ModeofPayment{
			ModeOfPaymentName: "MOP_ACTIVE",
			Enabled: true,
			Accounts: []ModeofPaymentAccount{
				{Company: "C1", DefaultAccount: "ACC_OK_1"},
				{Company: "C2", DefaultAccount: "ACC_OK_2"},
			},
		}
		assert.NoError(t, service.Validate(mop))
	})

	// 2. Failure Order Test 1: Repeating Companies (Highest Precedence)
	t.Run("Integration_Fail_RepeatingCompanies", func(t *testing.T) {
		mop := &ModeofPayment{
			ModeOfPaymentName: "MOP_FAIL",
			Enabled: true,
			Accounts: []ModeofPaymentAccount{
				{Company: "C1", DefaultAccount: "ACC_OK_1"},
				{Company: "C1", DefaultAccount: "ACC_OK_2"}, // Fails Step 1
			},
		}
		err := service.Validate(mop)
		var vErr *ValidationError
		assert.True(t, errors.As(err, &vErr))
		assert.Equal(t, 409, vErr.Code)
	})

	// 3. Failure Order Test 2: Account Mismatch (Mid Precedence)
	t.Run("Integration_Fail_AccountMismatch", func(t *testing.T) {
		mop := &ModeofPayment{
			ModeOfPaymentName: "MOP_FAIL_2",
			Enabled: true,
			Accounts: []ModeofPaymentAccount{
				{Company: "C1", DefaultAccount: "ACC_OK_1"},
				{Company: "C_WRONG", DefaultAccount: "ACC_OK_2"}, // Fails Step 2
			},
		}
		err := service.Validate(mop)
		var vErr *ValidationError
		assert.True(t, errors.As(err, &vErr))
		assert.Equal(t, 400, vErr.Code)
	})

	// 4. Failure Order Test 3: POS Usage Conflict (Lowest Precedence)
	t.Run("Integration_Fail_POSConflict", func(t *testing.T) {
		posConflictDB := &MockDBService{
			AccountCompanyMap: standardDB.AccountCompanyMap,
			POSUsage:          map[string][]string{"MOP_BLOCKED": {"P_Retail"}},
		}
		conflictService := &ModeofPaymentService{DB: posConflictDB}

		mop := &ModeofPayment{
			ModeOfPaymentName: "MOP_BLOCKED",
			Enabled: false, // Attempting to disable
			Accounts: []ModeofPaymentAccount{
				{Company: "C1", DefaultAccount: "ACC_OK_1"},
			},
		}
		err := conflictService.Validate(mop)
		var vErr *ValidationError
		assert.True(t, errors.As(err, &vErr))
		assert.Equal(t, 403, vErr.Code)
	})
}