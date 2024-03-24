package common

import (
	"fmt"
	"net"
	"time"
	"bufio"
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
}

const(
	BATCH_SIZE = 7
)

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

	// Create a goroutine to handle the signal in a non-blocking way
	go func() {
		// Wait for the signal
		<-sig
		// Close the connection
		log.Infof("action: sigterm_signal_handling | result: in_progress | client_id: %v", c.config.ID)
		c.conn.Close()
		log.Infof("action: closing_connection | result: success | client_id: %v", c.config.ID)
		log.Infof("action: sigterm_signal_handling | result: success | client_id: %v", c.config.ID)
	}()

	// Create the connection to the server and defer the close (close at the end)
	c.createClientSocket()
	defer c.conn.Close()
	filepath := fmt.Sprintf("./data/agency-%s.csv", c.config.ID)
	file, err := os.Open(filepath)
	if err != nil {
		log.Fatalf(
			"action: open_file | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}
	defer file.Close()
	scanner := bufio.NewScanner(file)

	for {
		// Read the corresponding file and extract a BATCH of bets to send to the server
		bets := read_bet_batch(BATCH_SIZE, scanner)
		if len(bets) == 0 {
			break
		}

		// If the batch is smaller than BATCH_SIZE, we send the remaining bets and finish
		if len(bets) < BATCH_SIZE {
			send_bets(c.conn, bets, c.config.ID)
			break
		}

		// Send the batch
		send_bets(c.conn, bets, c.config.ID)

		// Wait for the server to send ACK
		ack, err := ReceiveMessage(c.conn)
		if err != nil {
			log.Fatalf(
				"action: receive_message | result: fail | client_id: %v | error: %v",
				c.config.ID,
				err,
			)
		}
		if ack == "ACK" {
			log.Infof("action: batch_enviado | result: success | client_id: %v | message: %v", c.config.ID, ack)
		}
	}

	// Send the EOF message to the server
	eof := SendMessage(c.conn, "EOF\n")
	if eof != nil {
		log.Fatalf(
			"action: send_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			eof,
		)
	}

	// Wait for the server to send final ACK
	final_ack, err := ReceiveMessage(c.conn)
	if err != nil {
		log.Fatalf(
			"action: receive_message | result: fail | client_id: %v | error: %v",
			c.config.ID,
			err,
		)
	}
	if final_ack == "ACK" {
		log.Infof("action: apuestas_enviadas | result: success | client_id: %v | message: %v", c.config.ID, final_ack)
	}

	log.Infof("action: client_finished | result: success | client_id: %v", c.config.ID)

	// Close the signal channel to unblock the signal handling goroutine and exit the program
	close(sig)
}

func send_bets(conn net.Conn, bets []Bet, client_id string) {
	// Send the message to the server
	for _, bet := range bets {
		message := fmt.Sprintf("%s|%s|%s|%s|%s|%s\n", client_id, bet.Name, bet.Surname, bet.Gambler_id, bet.Birthdate, bet.Number)
		err := SendMessage(conn, message)
		if err != nil {
			log.Fatalf(
				"action: send_message | result: fail | client_id: %v | error: %v",
				client_id,
				err,
			)
		}
	}
}