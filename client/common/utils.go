package common

// This module is destined to hold common structures and functions

import (
	"bufio"
	"strings"
)

type Bet struct {
	Id string
	Name string
	Surname string
	Gambler_id string
	Birthdate string
	Number string
}

func read_bet_batch(batch int, scanner *bufio.Scanner) ([]Bet) {
	// This function reads a batch of bets from a csv file and returns a slice of Bet structs
	// The file must be in the format:
	// name,surname,gambler_id,birthdate,number
	// The function returns an error if the file cannot be read or if the file is not in the correct format
	bets := make([]Bet, 0)
	for i := 0; i < batch; i++ {
		scanner.Scan()
		line := scanner.Text()
		if line == "" {
			break
		}

		// Fill the bet struct
		splitted_line := strings.Split(line, ",")
		bet := Bet{
			Name: splitted_line[0],
			Surname: splitted_line[1],
			Gambler_id: splitted_line[2],
			Birthdate: splitted_line[3],
			Number: splitted_line[4],
		}
		bets = append(bets, bet)
	}
	return bets
}