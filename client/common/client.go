package common

import (
	"fmt"
	"net"
	"time"
	"os"
	"os/signal"
	"syscall"
	log "github.com/sirupsen/logrus"
)

// ClientConfig Configuration used by the client
type ClientConfig struct {
	ID            string
	ServerAddress string
	LoopLapse     time.Duration
	LoopPeriod    time.Duration
}

// Client Entity that encapsulates how
type Client struct {
	config ClientConfig
	conn   net.Conn
	Bet   Bet
}

// NewClient Initializes a new client receiving the configuration
// as a parameter
func NewClient(config ClientConfig) *Client {
	client := &Client{
		config: config,
	}
	return client
}

// CreateClientSocket Initializes client socket. In case of
// failure, error is printed in stdout/stderr and exit 1
// is returned
func (c *Client) createClientSocket() error {
	conn, err := net.Dial("tcp", c.config.ServerAddress)
	if err != nil {
		log.Fatalf(
	        "action: connect | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}
	c.conn = conn
	return nil
}

// Starts the client loop or execution of the client
func (c *Client) StartClientLoop() {
	// Handle SIGTERM to close the connection before exiting
	sig := make(chan os.Signal, 1)
	signal.Notify(sig, syscall.SIGTERM)

	// Create a channel to shutdown the client in case it's needed
	shutdown_channel := make(chan struct{})

	// Create a goroutine to handle the signal in a non-blocking way
	go func() {
		// Wait for the signal
		<-sig
		// Close the connection
		log.Infof("action: sigterm_signal_handling | result: in_progress | client_id: %v", c.config.ID)
		c.conn.Close()
		log.Infof("action: closing_connection | result: success | client_id: %v", c.config.ID)
		log.Infof("action: sigterm_signal_handling | result: success | client_id: %v", c.config.ID)
		close(shutdown_channel)
	}()

	// Verify if the shutdown channel was closed to exit the client execution in case of SIGTERM or normal exit
	select {
	case <-shutdown_channel:
		log.Infof("action: shutdown_detected | result: success | client_id: %v", c.config.ID)
		return
	default:
	}

	// Create the connection to the server and defer the close (close at the end)
	c.createClientSocket()

	// Create and format the message to send to the server using the bet information
	message := fmt.Sprintf(
		"%s|%s|%s|%s|%s|%s",
		c.Bet.Id,
		c.Bet.Name,
		c.Bet.Surname,
		c.Bet.Gambler_id,
		c.Bet.Birthdate,
		c.Bet.Number,
	)

	// Send the message to the server
	err := SendMessage(c.conn, message)
	if err != nil {
		log.Fatalf(
			"action: send_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}

	// Read the response from the server
	response, err := ReceiveMessage(c.conn)
	if err != nil {
		log.Fatalf(
			"action: receive_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}

	// Log the response from the server
	if response == "ACK" {
		log.Infof("action: apuesta_enviada | result: success | dni: %s | numero: %s", c.Bet.Gambler_id, c.Bet.Number)
	} else {
		log.Fatalf(
			"action: receive_message | result: apuesta_fallida | client_id: %s | response: %s",
			c.Bet.Id,
			response,
		)
	}


	log.Infof("action: client_finished | result: success | client_id: %v", c.config.ID)

	// Close the signal channel to unblock the signal handling goroutine and exit the program
	close(sig)
}
