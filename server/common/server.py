import select
import socket
import logging
import signal
import time
from common.communications import receive_message, send_message
from common.utils import Bet, store_bets, load_bets, has_won

TOTAL_AGENCIES = 5 # Since we are using a fixed number of agencies, we can define it as a constant

class Server:
    def __init__(self, port, listen_backlog, batch_size):
        # Initialize server socket
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind(('', port))
        self._server_socket.listen(listen_backlog)
        self._sigterm_received = False
        self._BATCH_SIZE = batch_size
        self._total_agencies_attended = 0
        self._agencies_sockets = {i: None for i in range(1, TOTAL_AGENCIES + 1)}

    def run(self):
        """
        Dummy Server loop

        Server that accept a new connections and establishes a
        communication with a client. After client with communucation
        finishes, servers starts to accept new connections again
        """

        signal.signal(signal.SIGTERM, self.__sigterm_handler)
        
        while not self._sigterm_received:
            client_sock = self.__accept_new_connection(timeout=0.1)
            if client_sock is not None:
                self.__handle_client_connection(client_sock)
        self._server_socket.close()
        # Close all the sockets of the agencies
        for _, sock in self._agencies_sockets.items():
            sock.close()
        logging.info("action: closing_server_socket | result: success")
        logging.info(f"action: sigterm_signal_handling | result: success")
        logging.info("action: server_shutdown | result: success")
        
    def __sigterm_handler(self, signum, frame):
        """
        Signal handler for SIGTERM to gracefully shutdown the server

        This function will be called when the server receives a SIGTERM
        signal. The server will set the sigterm_received flag to True and
        will stop accepting new connections.
        """

        self._sigterm_received = True
        logging.info(f"action: sigterm_signal_handling | result: in_progress")

    def __handle_client_connection(self, client_sock):
        """
        Read message from a specific client socket and closes the socket

        If a problem arises in the communication with the client, the
        client socket will also be closed
        """
        try:
            current_bets_received = 0
            while True:
                msg = receive_message(client_sock).decode('utf-8')
                if msg == "EOF\n":
                    send_message(client_sock, "ACK")
                    logging.info(f'action: all_batchs_saved | result: success | ip: {addr[0]} | msg: ACK')
                    self._total_agencies_attended += 1
                    if self._total_agencies_attended == TOTAL_AGENCIES:
                        self._proceed_to_draw_lottery()
                    break
                # Split the message into the bet information
                bet_info = msg.split("|")
                if self._agencies_sockets.get(bet_info[0]) is None:
                    self._agencies_sockets[bet_info[0]] = client_sock
                bet_info[5].replace("\n", "")
                addr = client_sock.getpeername()
                logging.info(f'action: receive_message | result: success | ip: {addr[0]} | msg: {msg}')
                
                # Create a new bet object and store it
                bet = Bet(*bet_info)
                store_bets([bet])
                logging.info(f'action: apuesta_almacenada | result: success | dni: {bet.document} | numero: {bet.number}')
                current_bets_received += 1

                if current_bets_received == self._BATCH_SIZE:
                    send_message(client_sock, "ACK")
                    logging.info(f'action: batch_saved | result: success | ip: {addr[0]} | msg: ACK')
                    current_bets_received = 0
        except OSError as e:
            logging.error("action: receive_message | result: fail | error: {e}")


    def __accept_new_connection(self, timeout):
        """
        Accept new connections with a timeout

        Function blocks until a connection to a client is made.
        Then connection created is printed and returned
        But if timeout is reached, None is returned and it means
        that either no client connected or a SIGTERM signal was received
        """

        start_time = time.time()
        while time.time() - start_time < timeout:
            logging.info('action: accept_connections | result: in_progress')
            ready, _, _ = select.select([self._server_socket], [], [], timeout)
            if ready: # Verifies if the server socket is ready to be read, avoiding a blocking call
                c, addr = self._server_socket.accept()
                logging.info(f'action: accept_connections | result: success | ip: {addr[0]}')
                return c
            if self._sigterm_received:
                break
        logging.info('action: accept_connections | result: timeout_exceeded')
        return None
    
    def _proceed_to_draw_lottery(self):
        """
        Function to draw the lottery winners

        This function will be called when all the agencies have sent their
        bets. It will get the winner bets and send the winners information
        to the respective agencies
        """
        logging.info(f'action: sorteo | result: success')
        winner_bets = []
        agencies_winners = {i: [] for i in range(1, TOTAL_AGENCIES + 1)}
        for bet in load_bets():
            if has_won(bet):
                winner_bets.append(bet)
        for bet in winner_bets:
            agencies_winners[bet.agency].append(bet)
        for agency, winners in agencies_winners.items():
            if self._agencies_sockets.get(str(agency)) is not None:
                send_message(self._agencies_sockets[str(agency)], "WINNERS")
                for winner in winners:
                    send_message(self._agencies_sockets[str(agency)], f"{winner.document}")
                send_message(self._agencies_sockets[str(agency)], "WINNERS_EOF\n")
                logging.info(f'action: winners_sent | result: success | agency: {agency}')
        logging.info(f'action: sorteo_finalizado | result: success')

            

