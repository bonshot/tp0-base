package common

// The purpose of this module is to separate responsabilities and make communication protocol reusable
// and independent from the client and server implementations or business logic.
// Also, we want to avoid short writes and make the communication protocol more robust.

import (
	"fmt"
	"net"
	"strconv"
)

// Sends a message through the connection with the following format:
// <header>|<message>, where <header> is the length of the message and <message> is the actual message
// The aim is to avoid short writes so it is guaranteed that the whole message is sent in one go
func SendMessage(conn net.Conn, message string) error {
	// Add the header to the message
	messageLength := len(message)
	header := fmt.Sprintf("%d", messageLength)
	finalMessage := header + "|" + message

	// Write the message to the connection until all bytes are written
	actualWriteSize := len(finalMessage)
	for actualWriteSize > 0 {
		n, err := conn.Write([]byte(finalMessage))
		if err != nil {
			return err
		}
		actualWriteSize -= n
		finalMessage = finalMessage[n:]
	}

	return nil
}

// Reads the header of the message from the connection. The header is the length of the message
func ReadHeader(conn net.Conn) (string, error) {
	// Read until the complete header is received, byte by byte
	header := ""
	for {
		b := make([]byte, 1)
		_, err := conn.Read(b)
		if err != nil {
			return "", err
		}
		if string(b) == "|" {
			break
		}
		header += string(b)
	}
	return header, nil
}

// Receives a message from the connection. The message is received in the following format:
// <header>|<message>, where <header> is the length of the message and <message> is the actual message
// The aim is to avoid short reads so it is guaranteed that the whole message is received in one go
func ReceiveMessage(conn net.Conn) (string, error) {
	// Buffer to store the message
	message := ""
	
	header, err := ReadHeader(conn)
	if err != nil {
		return "", err
	}

	// Parse the header to know how many bytes to read
	messageLength, err := strconv.Atoi(header)
	if err != nil {
		return "", err
	}

	// We read the message and concatenate it until we have read the whole message avoiding short reads
	actualReadSize := messageLength
	for {
		b := make([]byte, actualReadSize)
		_, err := conn.Read(b)
		if err != nil {
			return "", err
		}
		message += string(b)
		actualReadSize -= len(b)
		if len(message) == messageLength || actualReadSize == 0 {
			break
		}
	}

	return message, nil
}
