package main

type ValidationError struct {
	Message string
	Code    int
	Err     error
}

func (ve ValidationError) Error() string {
	return ve.Message
}

func (ve ValidationError) Unwrap() error {
	return ve.Err
}

type Document interface {
	// Define methods that would be used for DB operations
	Save() error
	Delete() error
}

type CustomsTariffNumber struct {
	Description *string
	TariffNumber string
}

func (ctn *CustomsTariffNumber) Save(db RowScanner) error {
	// Implement save logic here
	return nil
}

func (ctn *CustomsTariffNumber) Delete(db RowScanner) error {
	// Implement delete logic here
	return nil
}

type RowScanner interface {
	// Define methods for scanning rows from the database
	Scan(dest ...interface{}) error
}