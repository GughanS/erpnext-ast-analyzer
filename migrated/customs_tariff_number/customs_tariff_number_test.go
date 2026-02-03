package main

import (
	"errors"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
)

type MockRowScanner struct {
	mock.Mock
}

func (m *MockRowScanner) Scan(dest ...interface{}) error {
	args := m.Called(dest)
	return args.Error(0)
}

func TestValidationError_Error(t *testing.T) {
	ve := ValidationError{
		Message: "An error occurred",
		Code:    400,
		Err:     nil,
	}

	assert.Equal(t, "An error occurred", ve.Error())
}

func TestValidationError_Unwrap(t *testing.T) {
	innerErr := errors.New("inner error")
	ve := ValidationError{
		Message: "An error occurred",
		Code:    400,
		Err:     innerErr,
	}

	var vErr *ValidationError
	err := errors.Unwrap(ve)

	assert.True(t, errors.As(err, &vErr))
	assert.Equal(t, innerErr, vErr.Unwrap())
}

func TestCustomsTariffNumber_Save(t *testing.T) {
	mockDB := new(MockRowScanner)
	ctn := &CustomsTariffNumber{
		Description: nil,
		TariffNumber: "123456",
	}

	err := ctn.Save(mockDB)
	assert.NoError(t, err)
}

func TestCustomsTariffNumber_Delete(t *testing.T) {
	mockDB := new(MockRowScanner)
	ctn := &CustomsTariffNumber{
		Description: nil,
		TariffNumber: "123456",
	}

	err := ctn.Delete(mockDB)
	assert.NoError(t, err)
}